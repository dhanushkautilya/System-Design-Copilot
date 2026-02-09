from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .agent import AgenticCopilot
from .database import SessionLocal, Submission, init_db
from .schemas import InputPayload, OutputPayload, SubmissionResponse

init_db()
app = FastAPI(title="System Design Copilot", version="0.1.0")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"]
    ,
    allow_headers=["*"],
)

# Simple in-memory token bucket per IP
_RATE_LIMIT = {"tokens": {}, "capacity": 120, "refill_rate": 2}  # tokens per second


def rate_limiter(request: Request):
    ip = request.client.host if request.client else "anon"
    now = time.time()
    tokens = _RATE_LIMIT["tokens"].get(ip, {"tokens": _RATE_LIMIT["capacity"], "ts": now})
    # refill
    elapsed = now - tokens["ts"]
    tokens["tokens"] = min(_RATE_LIMIT["capacity"], tokens["tokens"] + elapsed * _RATE_LIMIT["refill_rate"])
    tokens["ts"] = now
    if tokens["tokens"] < 1:
        _RATE_LIMIT["tokens"][ip] = tokens
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    tokens["tokens"] -= 1
    _RATE_LIMIT["tokens"][ip] = tokens


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


copilot = AgenticCopilot()


@app.get("/", response_class=HTMLResponse)
def root():
    # Serve frontend index
    index_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if index_path.exists():
        return index_path.read_text()
    return "Frontend not built yet."


@app.post("/api/validate")
async def validate(payload: Dict, _: None = Depends(rate_limiter)):
    try:
        InputPayload(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors())
    return {"valid": True}


@app.post("/api/estimate")
async def estimate(payload: Dict, _: None = Depends(rate_limiter)):
    try:
        inp = InputPayload(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors())
    qps = copilot._sizing({"input": inp.model_dump()})["sizing"]["qps"]
    return {"qps": qps}


@app.post("/api/analyze", response_model=OutputPayload)
async def analyze(payload: Dict, request: Request, db=Depends(get_db), _: None = Depends(rate_limiter)):
    try:
        inp = InputPayload(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors())

    result = copilot.run(inp)
    output = OutputPayload(**result)

    submission = Submission(
        title=inp.app_name,
        input_json=json.dumps(inp.model_dump()),
        output_json=json.dumps(output.model_dump()),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    output.submission_id = submission.id
    return output


@app.get("/api/submissions")
async def list_submissions(db=Depends(get_db), _: None = Depends(rate_limiter)):
    rows = db.query(Submission).order_by(Submission.created_at.desc()).all()
    return {"submissions": [SubmissionResponse(**row.to_dict()).model_dump() for row in rows]}


@app.get("/api/submissions/{submission_id}")
async def get_submission(submission_id: int, db=Depends(get_db), _: None = Depends(rate_limiter)):
    row = db.query(Submission).filter(Submission.id == submission_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return SubmissionResponse(**row.to_dict())


def build_markdown(output: OutputPayload) -> str:
    md = [f"# Architecture Report", f"## Summary\n{output.summary}"]
    md.append("## Assumptions\n" + "\n".join(f"- {a}" for a in output.assumptions))
    md.append("## Architecture Options")
    for opt in output.architecture_options:
        md.append(f"### {opt.title}\n" + "\n".join(f"- {b}" for b in opt.bullets))
    md.append(f"## Recommendation\n{output.recommended_option}")
    md.append("## Tech Stack\n" + "\n".join(f"- {t}" for t in output.tech_stack))
    md.append("## Sizing\n```json\n" + json.dumps(output.sizing, indent=2) + "\n```")
    md.append("## APIs")
    for api in output.api_design:
        md.append(f"### {api.method} {api.path}\n{api.description}\n" +
                  f"**Request**\n```json\n{json.dumps(api.request, indent=2)}\n```\n" +
                  f"**Response**\n```json\n{json.dumps(api.response, indent=2)}\n```")
    md.append("## Performance\n" + "\n".join(f"- {p}" for p in output.performance_plan))
    md.append("## Security\n" + "\n".join(f"- {s}" for s in output.security_plan))
    md.append("## Reliability\n" + "\n".join(f"- {r}" for r in output.reliability_plan))
    md.append("## Risks\n" + "\n".join(f"- {r}" for r in output.risks))
    md.append("## Phased Rollout\n" + "\n".join(f"- {p}" for p in output.phased_rollout))
    md.append("## Diagrams\n````mermaid\n" + output.mermaid_flow + "\n````\n````mermaid\n" + output.mermaid_components + "\n````")
    return "\n\n".join(md)


@app.get("/api/submissions/{submission_id}/download", response_class=PlainTextResponse)
async def download_markdown(submission_id: int, db=Depends(get_db), _: None = Depends(rate_limiter)):
    row = db.query(Submission).filter(Submission.id == submission_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    output = OutputPayload(**json.loads(row.output_json))
    return PlainTextResponse(build_markdown(output))


# Mount static frontend (optional)
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}
