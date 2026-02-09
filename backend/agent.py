import json
import operator
import os
from typing import Annotated, Any, Dict, List, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import END, StateGraph

from .schemas import InputPayload
from .tools import calc_qps, calc_storage, generate_mermaid_components, generate_mermaid_flow, risk_checklist


class AgentState(TypedDict):
    input: Dict[str, Any]
    assumptions: Annotated[List[str], operator.add]
    plan_steps: Annotated[List[str], operator.add]
    sizing: Dict[str, Any]
    architecture_options: List[Dict[str, Any]]
    recommended_option: str
    mermaid_flow: str
    mermaid_components: str
    api_design: List[Dict[str, Any]]
    performance_plan: List[str]
    reliability_plan: List[str]
    security_plan: List[str]
    threat_model: List[str]
    observability: List[str]
    summary: str
    tech_stack: List[str]
    risks: List[str]
    phased_rollout: List[str]


class AgenticCopilot:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        self.mock_mode = not bool(api_key)
        if not self.mock_mode:
            self.llm = ChatOpenAI(temperature=0.2, model="gpt-4o-mini")
        else:
            self.llm = None
        self.workflow = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("intake_validate", self._intake_validate)
        graph.add_node("planner", self._planner)
        graph.add_node("sizing_estimator", self._sizing)
        graph.add_node("architecture_generator", self._architecture)
        graph.add_node("api_designer", self._apis)
        graph.add_node("performance_reliability", self._perf_rel)
        graph.add_node("security_compliance", self._security)
        graph.add_node("final_report", self._final)

        graph.set_entry_point("intake_validate")
        graph.add_edge("intake_validate", "planner")
        graph.add_edge("planner", "sizing_estimator")
        graph.add_edge("sizing_estimator", "architecture_generator")
        graph.add_edge("architecture_generator", "api_designer")
        graph.add_edge("api_designer", "performance_reliability")
        graph.add_edge("performance_reliability", "security_compliance")
        graph.add_edge("security_compliance", "final_report")
        graph.add_edge("final_report", END)
        return graph.compile()

    def run(self, payload: InputPayload) -> Dict[str, Any]:
        state: Dict[str, Any] = {"input": payload.model_dump()}
        return self.workflow.invoke(state)

    def _call_llm(self, system_prompt: str, user_prompt: str, fallback: Any = None) -> Any:
        if self.mock_mode:
            return fallback
        try:
            messages = [
                SystemMessage(content=system_prompt + "\nRespond ONLY with valid JSON. Do not include markdown code blocks or explanations."),
                HumanMessage(content=user_prompt)
            ]
            res = self.llm.invoke(messages)
            # Remove markdown code blocks if any
            content = res.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            return json.loads(content)
        except Exception as e:
            print(f"LLM Error: {e}")
            return fallback

    # Node implementations
    def _intake_validate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        inp = InputPayload(**state["input"])
        return {"input": inp.model_dump(), "assumptions": ["Inputs normalized"], "notes": []}

    def _planner(self, state: Dict[str, Any]) -> Dict[str, Any]:
        inp = state["input"]
        pat = inp.get("traffic_pattern", "steady")
        assumptions = [
            f"Traffic pattern is {pat} with peak {inp['peak_rps']} rps",
            f"Regions: {', '.join(inp['regions'])}",
            f"Budget level: {inp['budget_level']}",
        ]
        if inp.get("domain"):
            assumptions.append(f"Application domain: {inp['domain']}")
        needed = [
            "sizing", "architecture", "api", "performance", "security", "reliability",
        ]
        return {"assumptions": assumptions, "plan_steps": needed}

    def _sizing(self, state: Dict[str, Any]) -> Dict[str, Any]:
        inp = state["input"]
        pat = inp.get("traffic_pattern") or "steady"
        multiplier = 1.8 if pat == "spiky" else 1.4
        peak_concurrency = inp.get("peak_concurrent_users") or (inp["dau"] // 10)
        qps = calc_qps(inp["dau"], peak_concurrency, inp["read_write_ratio"], multiplier)
        storage = calc_storage(records_per_user=12, avg_record_size_kb=8, retention_days=365, dau=inp["dau"])
        bandwidth_gbps = round(qps["peak_qps"] * 2 * 1024 / 1e6, 3)  # assume 2KB avg payload
        sizing = {"qps": qps, "storage": storage, "bandwidth_gbps": bandwidth_gbps}
        return {"sizing": sizing}

    def _architecture(self, state: Dict[str, Any]) -> Dict[str, Any]:
        inp = state["input"]
        sys_p = "You are a senior system architect. Generate architecture options for a new app."
        user_p = f"""
        App: {inp['app_name']}
        Description: {inp['description']}
        Scale: {inp['dau']} DAU, {inp['peak_rps']} Peak RPS
        Budget: {inp['budget_level']}

        Return a JSON object with:
        1. 'options': list of 2 options. Each with 'title' and 'bullets' (list of strings).
        2. 'recommended_option': the title of the best option.
        3. 'flows': list of mermaid-style edges (e.g. 'A[User]->B[LB]').
        4. 'components': list of mermaid-style nodes (e.g. 'A[User]').
        """
        default_options = [
            {"title": "MVP (monolith)", "bullets": ["FastAPI + SQLite (dev) / Postgres (prod)", "Redis cache"]},
            {"title": "Scale-out", "bullets": ["Microservices on K8s", "Managed DB (RDS)", "Kafka for async"]}
        ]
        fallback = {
            "options": default_options,
            "recommended_option": "MVP (monolith)" if inp["budget_level"] == "low" else "Scale-out",
            "flows": ["A[Client]-->B[LB]", "B-->C[App Server]", "C-->D[(Database)]"],
            "components": ["A[Client]", "B[LB]", "C[App Server]", "D[(Database)]"]
        }

        res = self._call_llm(sys_p, user_p, fallback=fallback)
        
        return {
            "architecture_options": res.get("options", default_options),
            "recommended_option": res.get("recommended_option", fallback["recommended_option"]),
            "mermaid_flow": generate_mermaid_flow(res.get("components", fallback["components"]), res.get("flows", fallback["flows"])),
            "mermaid_components": generate_mermaid_components(res.get("components", fallback["components"]))
        }

    def _apis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        inp = state["input"]
        sys_p = "You are a senior API designer. Generate relevant API endpoints for this app."
        user_p = f"""
        App: {inp['app_name']}
        Description: {inp['description']}
        
        Return a JSON list of 3-4 API objects. Each object with: 
        'method', 'path', 'description', 'request' (dict), 'response' (dict), 'rate_limit_rpm' (int), 'idempotent' (bool).
        """
        fallback = [
            {
                "method": "POST",
                "path": "/api/v1/resource",
                "description": "Create a new resource.",
                "request": {"name": "string"},
                "response": {"id": "string"},
                "rate_limit_rpm": 60,
                "idempotent": False,
            }
        ]
        res = self._call_llm(sys_p, user_p, fallback=fallback)
        return {"api_design": res}

    def _perf_rel(self, state: Dict[str, Any]) -> Dict[str, Any]:
        sizing = state.get("sizing", {})
        performance = [
            "Edge CDN for static assets, API behind reverse proxy with HTTP keep-alive",
            "Redis caching with 70-90% target hit rate for read-heavy endpoints",
            "Async workers for generating reports; queue depth alarms",
            "Pagination + index on created_at for submissions table",
            "Blue/green deploys and feature flags for rollouts",
        ]
        reliability = [
            "SLO: 99.5% availability, p95 < 400ms for analyze endpoint",
            "Retries with jitter for downstream LLM calls, idempotency keys on POST",
            "Backups daily, PITR for Postgres, replica in second region for DR (RPO 1h, RTO 4h)",
            "Health checks, autoscale based on queue length and CPU",
        ]
        return {"performance_plan": performance, "reliability_plan": reliability}

    def _security(self, state: Dict[str, Any]) -> Dict[str, Any]:
        inp = state["input"]
        sys_p = "You are a security architect. Generate a security plan and threat model."
        user_p = f"""
        App: {inp['app_name']}
        Domain: {inp.get('domain', 'general')}
        Compliance: {', '.join(inp.get('compliance', []))}
        Data Types: {', '.join(inp.get('data_types', []))}

        Return a JSON object with:
        1. 'security_plan': list of 5 security measures.
        2. 'threat_model': list of 3 potential threats.
        3. 'observability': list of 4 monitoring/logging measures.
        """
        fallback_threats = risk_checklist(inp.get("compliance") or ["SOC2", "GDPR"], inp.get("data_types") or ["PII"])
        fallback = {
            "security_plan": ["AuthN with OIDC", "mTLS", "Secrets Vault", "WAF", "Encryption at rest"],
            "threat_model": fallback_threats,
            "observability": ["Prometheus metrics", "ELK logging", "Jaeger tracing", "PagerDuty alerts"]
        }
        res = self._call_llm(sys_p, user_p, fallback=fallback)
        return {
            "security_plan": res.get("security_plan", fallback["security_plan"]),
            "threat_model": res.get("threat_model", fallback["threat_model"]),
            "observability": res.get("observability", fallback["observability"])
        }

    def _final(self, state: Dict[str, Any]) -> Dict[str, Any]:
        inp = state["input"]
        sys_p = "You are a senior technical lead. Finalize the system design report."
        user_p = f"""
        App: {inp['app_name']}
        Description: {inp['description']}
        Scale: {inp['dau']} DAU
        Budget: {inp['budget_level']}
        Architecture Recommended: {state.get('recommended_option')}

        Return a JSON object with:
        1. 'summary': 1-2 sentence high-level summary.
        2. 'tech_stack': list of 6-7 specific technologies (e.g. 'Frontend: React', 'DB: Postgres').
        3. 'phased_rollout': list of 3 phases (MVP, v2, v3).
        """
        fallback = {
            "summary": f"System design for {inp['app_name']} supporting {inp['dau']} DAU.",
            "tech_stack": ["FastAPI", "Postgres", "Redis", "Docker", "AWS"],
            "phased_rollout": ["Phase 1: MVP", "Phase 2: Scale", "Phase 3: Global"]
        }
        res = self._call_llm(sys_p, user_p, fallback=fallback)

        sizing = state.get("sizing", {})
        risks = (state.get("threat_model") or []) + [
            "LLM dependency latency/availability; keep mock fallback",
            "Cost overrun if prompt volume spikes; add budget guardrails",
        ]

        # Deduplicate assumptions
        unique_assumptions = []
        seen = set()
        for a in (state.get("assumptions") or []):
            if a not in seen:
                unique_assumptions.append(a)
                seen.add(a)

        return {
            "summary": res.get("summary", fallback["summary"]),
            "assumptions": unique_assumptions,
            "architecture_options": state.get("architecture_options") or [],
            "recommended_option": state.get("recommended_option") or "N/A",
            "tech_stack": res.get("tech_stack", fallback["tech_stack"]),
            "sizing": sizing,
            "api_design": state.get("api_design") or [],
            "performance_plan": state.get("performance_plan") or [],
            "security_plan": state.get("security_plan") or [],
            "reliability_plan": state.get("reliability_plan") or [],
            "risks": risks,
            "phased_rollout": res.get("phased_rollout", fallback["phased_rollout"]),
            "mermaid_flow": state.get("mermaid_flow") or "",
            "mermaid_components": state.get("mermaid_components") or "",
            "observability": state.get("observability") or [],
            "threat_model": state.get("threat_model") or [],
        }
