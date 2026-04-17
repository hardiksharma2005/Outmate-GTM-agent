# OutMate — Multi-Agent GTM Intelligence Engine

OutMate is an AI-powered Go-To-Market intelligence platform. You describe your ideal customer in plain English; a 5-agent pipeline powered by Claude identifies matching companies, scores them, detects buying signals, and generates personalized outbound strategy — all streamed to you in real time.

---

## Demo

> **Example query:** *"Find Series B SaaS companies in the US with recent funding, hiring sales roles, and using Salesforce"*

The pipeline returns ranked companies with ICP scores, buying signals, email templates, and persona-specific sales plays.

---

## How It Works

```
Natural Language Query
  → Planner      — parse intent into structured execution plan
  → Retrieval    — filter company database (LRU-cached)
  → Enrichment   — score ICP fit, detect buying signals (rule-based)
  → Critic       — validate results; reject + self-correct if needed
  → GTM Strategy — generate hooks, email snippets, persona plays
  → Structured GTMResponse (streamed via SSE)
```

On a Critic rejection, the pipeline automatically strips hallucinated filters, injects correction context, and retries (up to 3×) — no manual intervention needed.

---

## Features

- **Multi-agent orchestration** — 5 specialized agents run sequentially with self-correcting retry loop
- **ICP scoring** — composite score across Fit (45%), Intent (35%), Growth (20%) with Hot/Warm/Nurture/Excluded tiers
- **7 buying signals** — HIRING_EXPANSION, RECENT_FUNDING, HIGH_GROWTH, TECH_FIT, SERIES_SWEET_SPOT, HIRING_SALES_ROLES, COMPETITIVE_DISPLACEMENT
- **GTM strategy generation** — hooks, angles, email snippets, persona-specific plays for top 8 companies
- **Real-time SSE streaming** — watch each agent complete live in the UI
- **Weighted confidence score** — aggregated across all agents with retry penalty

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, FastAPI, Uvicorn |
| AI | Anthropic Claude (SDK 0.34+) |
| Validation | Pydantic v2 |
| Frontend | React 19, TypeScript, Vite |
| Streaming | Server-Sent Events (SSE) |

---

## Project Structure

```
outmate agent/
├── backend/
│   ├── agents/              # 5 agents: planner, retrieval, enrichment, critic, gtm_strategy
│   ├── orchestrator/        # Pipeline runner + retry manager
│   ├── memory/              # LRU cache + per-session state & SSE queues
│   ├── models/              # Pydantic schemas (GTMResponse, AgentEvent, etc.)
│   ├── tools/               # LLM client, ICP scorer, signal detector, mock data API
│   └── main.py              # FastAPI app + shared singletons
└── frontend/
    └── src/
        ├── components/      # AgentTimeline, ResultCard, GTMStrategyPanel, etc.
        ├── hooks/           # useGTMQuery (state machine), useSSE (EventSource)
        └── types/           # TypeScript interfaces
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)

### Backend

```bash
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Add your ANTHROPIC_API_KEY to backend/.env
python -m backend.main
# Server starts on http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:5173
```

The Vite dev server proxies API calls to `:8000` automatically.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Your Anthropic API key |
| `MODEL_NAME` | `claude-sonnet-4-6` | Claude model to use |
| `MAX_RETRIES` | `3` | Max critic retry attempts |
| `RATE_LIMIT_RPM` | `60` | API requests per minute |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/query` | Submit a query; returns `session_id` |
| `GET` | `/api/stream/{session_id}` | SSE stream of agent events |
| `GET` | `/api/result/{session_id}` | Final `GTMResponse` JSON |
| `GET` | `/api/health` | Health check (no API key required) |

### GTMResponse shape

```json
{
  "session_id": "...",
  "query": "...",
  "plan": { "target_criteria": {}, "personas": [], "buying_signals_requested": [] },
  "results": [{ "company": {}, "signals": [], "icp_score": {}, "enrichment_notes": "" }],
  "gtm_strategy": { "hooks": [], "angles": [], "email_snippets": [], "persona_plays": [] },
  "confidence": 0.87,
  "reasoning_trace": [],
  "retry_count": 0
}
```

### AgentEvent (SSE wire format)

```json
{
  "event_type": "AGENT_START | AGENT_COMPLETE | AGENT_RETRY | STREAM_CHUNK | PLAN_READY | FINAL_OUTPUT | ERROR",
  "agent": "planner | retrieval | enrichment | critic | gtm_strategy | orchestrator",
  "payload": {},
  "timestamp": 1234567890.5,
  "session_id": "..."
}
```

---

## ICP Scoring

| Dimension | Weight | Signals |
|---|---|---|
| **Fit** | 45% | Industry, company size, tech overlap, geography, funding stage |
| **Intent** | 35% | Sales hiring, recent funding, hiring velocity, news, growth |
| **Growth** | 20% | YoY revenue growth, scaled by size and funding recency |

| Score | Tier |
|---|---|
| ≥ 0.75 | 🔥 Hot |
| ≥ 0.55 | Warm |
| ≥ 0.35 | Nurture |
| < 0.35 | Excluded |

---

## Confidence Score

The final confidence is a weighted average across all agents, with a penalty per retry:

```
confidence = planner×0.10 + retrieval×0.20 + enrichment×0.25
           + critic×0.30 + gtm_strategy×0.15 − retry_count×0.05
```

---

## Architecture Notes

- **Shared singletons** — `_shared_llm`, `_shared_cache`, `_shared_rate_limiter` are created once in `main.py` and injected into every orchestrator instance. Agents never create their own LLM client.
- **Critic self-correction** — On rejection, hallucinated filter keys are stripped, correction context is injected into the pipeline dict, and the retrieval cache prefix is invalidated before retry.
- **Rule-based enrichment** — ICP scoring and signal detection use no LLM calls; they are deterministic and fast.
- **JSON-only agent outputs** — All system prompts require raw JSON. Markdown fences are stripped automatically.
- **Session cleanup** — Sessions older than 1 hour are purged every 10 minutes.

---

## License

MIT
