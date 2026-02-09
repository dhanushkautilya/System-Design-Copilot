# AI System Design Copilot

An AI-powered architect that transforms high-level product requirements into production-ready system design reports using **LangGraph** and **GPT-4o-mini**.

## 🚀 Key Features

- **AI-Driven Dynamic Design**: Unlike static templates, the Copilot uses an LLM to generate custom architectures, tech stacks, and security plans based on your specific scale, budget, and domain.
- **Interactive UI**: A sleek, dark-mode dashboard featuring:
  - **Dynamic Diagrams**: Auto-generated Mermaid.js flowcharts and component maps.
  - **Interactive Tooltips**: Clickable "i" icons providing contextual guidance for every input field.
  - **Optional Param Accordion**: Deep-dive into advanced configurations (Compliance, Data Types, Latency Targets) only when you need them.
- **Production-Grade Outputs**: Generates comprehensive reports including API designs (with rate limits), sizing estimations (QPS/Storage), and security threat models.
- **Exportable Reports**: One-click "Download Markdown" for all generated designs.

## 🛠️ Stack

- **Backend**: FastAPI, LangGraph, Pydantic v2
- **Intelligence**: OpenAI GPT-4o-mini (via LangChain)
- **Database**: SQLite (SQLAlchemy)
- **Frontend**: Vanilla JS, Tailwind CSS, Mermaid.js

## 🏁 Quick Start

### 1. Setup Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Configure API Key
```bash
export OPENAI_API_KEY='your-api-key-here'
```

### 3. Run the App
```bash
uvicorn backend.main:app --reload --port 8000
```
Visit `http://localhost:8000` to start designing.

## 🧪 Testing

Run the validation and tool suite:
```bash
pytest
```

## 📝 Example Core Input

The AI focuses on these 7 core drivers to shape your architecture:
```json
{
  "app_name": "GlobalPay",
  "description": "Cross-border B2B payouts.",
  "dau": 1000000,
  "peak_rps": 5000,
  "read_write_ratio": 1.5,
  "regions": ["us-east", "eu-west"],
  "budget_level": "high"
}
```

## 🛡️ License
MIT
