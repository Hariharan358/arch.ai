# Mark AI — The Intelligence Marketplace

> **Marketplace for AI agents.** A marketplace where AI agents autonomously search, purchase, and execute pre-solved reasoning workflows — saving 70%+ tokens and eliminating repeated planning waste.

Built at [TreeHacks 2026](https://www.treehacks.com/)

---

## The Problem

Every time an AI agent encounters a task — filing Ohio taxes, parsing a Stripe invoice, comparing laptops — it starts from scratch. It burns tokens re-deriving domain knowledge that thousands of other agents have already figured out.

- **10–25% of all tokens** wasted on planning (decomposing tasks, deciding tool calls, handling errors)
- Same hyper-specific tasks get re-solved **millions of times** across agents worldwide
- Too specific to train separate models, but common enough to be enormously valuable

## The Solution

A marketplace of **reusable reasoning workflows** — hyper-specific, battle-tested solution templates that agents buy and execute locally with their own private data.

```bash
pip install archaitools
```

```python
from archaitools import MarkClient

mark = MarkClient(api_key="mk_...")

# Agent autonomously: estimate → buy → execute → rate
receipt = mark.solve("File Ohio 2024 taxes with W2 and itemized deductions")
print(f"Tokens saved: {receipt.tokens_saved}")  # ~10,000 tokens
```

Three lines of code. Any AI agent (Claude, GPT-4, LangChain) gets access to an ever-growing library of expert-level domain knowledge.

---

## Table of Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [SDK — `archaitools`](#sdk--archaitools)
- [API Reference](#api-reference)
- [Search Algorithm](#search-algorithm)
- [Dynamic Pricing](#dynamic-pricing)
- [Privacy Architecture](#privacy-architecture)
- [Deployment](#deployment)
- [Demo](#demo)
- [License](#license)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Mark AI Platform                       │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │  Next.js App │───▶│  Flask API   │───▶│ Elasticsearch  │  │
│  │  (frontend)  │    │  (backend)   │    │  (serverless)  │  │
│  └─────────────┘    └──────┬───────┘    └────────────────┘  │
│                            │                                  │
│                     ┌──────┴───────┐                         │
│                     │   Services   │                         │
│                     ├──────────────┤                         │
│                     │ Claude (LLM) │                         │
│                     │ JINA (embed) │                         │
│                     │ Supabase     │                         │
│                     │ Visa Direct  │                         │
│                     └──────────────┘                         │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    archaitools SDK                        │ │
│  │  pip install archaitools                                 │ │
│  │  Agents call: estimate → buy → execute → rate            │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Elasticsearch Two-Index Design

Two separate indices instead of one monolithic store:

| Index | Purpose | Content |
|-------|---------|---------|
| `workflows` | Broad search | Full workflow metadata + 1024-dim JINA embeddings |
| `workflows_nodes` | Tree-aware search | Individual steps within workflows + embeddings |

This gives **25% faster** workflow search and **75% faster** node-level search at scale (1,000+ workflows) by eliminating cross-type filter overhead and keeping each index in its own semantic space.

---

## Project Structure

```
mark-ai/
├── app/                          # Next.js pages (App Router)
│   ├── page.tsx                  #   Landing page
│   ├── layout.tsx                #   Root layout
│   ├── globals.css               #   Global styles
│   ├── auth/                     #   Auth flows (login, signup, callback)
│   ├── dashboard/                #   User dashboard
│   ├── marketplace/              #   Browse & purchase workflows
│   ├── sdk/                      #   SDK documentation page
│   └── workflow/                 #   Workflow visualization
│
├── components/                   # React components
│   ├── AgentChat.tsx             #   Live agent chat interface
│   ├── Dashboard.tsx             #   Token balance & history
│   ├── Hero.tsx                  #   Landing hero section
│   ├── HowItWorks.tsx            #   Feature walkthrough
│   ├── Marketplace.tsx           #   Workflow grid
│   ├── Nav.tsx                   #   Navigation bar
│   ├── PricingBreakdown.tsx      #   Pricing calculation display
│   ├── PurchaseModal.tsx         #   Purchase confirmation modal
│   ├── WorkflowCard.tsx          #   Workflow listing card
│   ├── WorkflowVisualizer.tsx    #   DAG/tree visualization
│   └── VisaPayment.tsx           #   Visa payment integration
│
├── backend/                      # Flask API server
│   ├── api.py                    #   Main app — all REST endpoints
│   ├── config.py                 #   Environment & configuration
│   ├── models.py                 #   Dataclasses (Workflow, DAG, etc.)
│   ├── matcher.py                #   Embedding-based workflow matching
│   ├── sanitizer.py              #   PII removal from queries
│   ├── pricing.py                #   Dynamic pricing engine
│   ├── orchestrator.py           #   Multi-step task orchestration
│   ├── query_decomposer.py       #   Recursive query decomposition
│   ├── recomposer.py             #   DAG recomposition
│   ├── agent.py                  #   Claude agent integration
│   ├── commerce.py               #   Token economy & purchases
│   ├── elastic_client.py         #   Elasticsearch client wrapper
│   ├── visa_payments.py          #   Visa CyberSource + Direct
│   ├── workflow_loader.py        #   Workflow JSON loader
│   ├── workflows.json            #   Workflow definitions
│   ├── services/                 #   Service modules
│   │   ├── cache_service.py      #     Response caching
│   │   ├── claude_service.py     #     Anthropic Claude client
│   │   ├── elasticsearch_service.py  # ES operations
│   │   └── embedding_service.py  #     JINA embedding client
│   └── requirements.txt          #   Python dependencies
│
├── marktools/                    # Python SDK package
│   ├── src/marktools/            #   Package source
│   ├── tests/                    #   Test suite
│   ├── pyproject.toml            #   Package config
│   └── LICENSE                   #   MIT license
│
├── agent-sdk/                    # Agent demo scripts
│   ├── tax_agent.py              #   Ohio tax filing agent
│   ├── shopping_agent.py         #   Product comparison agent
│   ├── orchestrator_agent.py     #   Multi-task chaining agent
│   ├── run_all.py                #   Run all demos
│   └── scenarios.py              #   Demo scenarios
│
├── demo/                         # Pitch demo
│   ├── run_demo.py               #   Self-contained demo runner
│   ├── with_archaitools.py       #   Agent with archaitools
│   ├── without_archaitools.py    #   Baseline agent (no archaitools)
│   └── benchmark_suite.py        #   Performance benchmarks
│
├── lib/supabase/                 # Supabase client helpers
├── middleware.ts                 # Next.js auth middleware
├── next.config.mjs               # Next.js config
├── vercel.json                   # Vercel deployment config
├── render.yaml                   # Render deployment config
└── package.json                  # Node.js dependencies
```

---

## Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| Flask 3.0 | REST API framework |
| Anthropic Claude | LLM for query decomposition & scoring |
| JINA Embeddings v3 | 1024-dim vectors for semantic search |
| Elasticsearch Serverless | Hybrid kNN + BM25 search |
| Supabase | Auth, user balances, transaction history |
| Visa CyberSource + Direct | Payment processing & instant creator payouts |

### Frontend
| Technology | Purpose |
|------------|---------|
| Next.js 14 | React framework (App Router) |
| TypeScript | Type safety |
| Framer Motion | Animations |
| Supabase SSR | Auth & session management |

### SDK
| Technology | Purpose |
|------------|---------|
| Python 3.9+ | Package runtime |
| Pydantic v2 | Type-safe models |
| Requests | HTTP client |
| Adapters for Anthropic, OpenAI, LangChain | Framework integrations |

---

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- API keys: Anthropic, JINA, Elasticsearch (optional for local dev — in-memory fallback available)

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env   # Add your API keys

python api.py
```

The API starts at `http://localhost:5001`. Without Elasticsearch credentials it falls back to in-memory search.

### 2. Frontend

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

### 3. SDK (optional)

```bash
pip install archaitools
```

Or install from source:

```bash
cd marktools && pip install -e ".[all]"
```

### Environment Variables

**Backend** (`.env`):
```
ANTHROPIC_API_KEY=sk-ant-...
JINA_API_KEY=jina_...
ELASTIC_CLOUD_ID=...          # optional
ELASTIC_API_KEY=...           # optional
VISA_API_KEY=...              # optional
VISA_SECRET_KEY=...           # optional
```

**Frontend** (`.env.local`):
```
NEXT_PUBLIC_SUPABASE_URL=https://...supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_API_URL=http://localhost:5001
```

---

## SDK — `archaitools`

The Python SDK that lets any AI agent tap into the marketplace.

### Installation

```bash
pip install archaitools                   # core
pip install archaitools[anthropic]        # + Claude support
pip install archaitools[openai]           # + OpenAI support
pip install archaitools[all]              # everything
```

### Usage with Claude

```python
import anthropic
from archaitools import MarkTools

client = anthropic.Anthropic()
tools = MarkTools(api_key="mk_...")

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=tools.to_anthropic(),
    messages=[{"role": "user", "content": "File my Ohio 2024 taxes, W2, itemized"}],
)
```

### Usage with OpenAI

```python
from openai import OpenAI
from archaitools import MarkTools

client = OpenAI()
tools = MarkTools(api_key="mk_...")

response = client.chat.completions.create(
    model="gpt-4",
    tools=tools.to_openai(),
    messages=[{"role": "user", "content": "File my Ohio 2024 taxes"}],
)
```

### Direct Client

```python
from archaitools import MarkClient

mark = MarkClient(api_key="mk_...")
receipt = mark.solve("File Ohio 2024 taxes with W2 and itemized deductions")
```

### Tool Reference

| Tool | Cost | Description |
|------|------|-------------|
| `mark_estimate` | Free | Search marketplace, get pricing & ranked solutions |
| `mark_buy` | Credits | Purchase solution, get full execution plan |
| `mark_rate` | Free | Rate a workflow after execution |
| `mark_search` | Free | Browse/filter available workflows |

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/search` | Semantic workflow search |
| `POST` | `/api/purchase` | Purchase a workflow |
| `POST` | `/api/feedback` | Rate a workflow (up/down) |
| `POST` | `/api/sanitize` | Demo PII sanitization |
| `GET`  | `/api/workflows` | List all workflows |
| `GET`  | `/api/pricing/<id>` | Detailed pricing breakdown |
| `GET`  | `/health` | Health check |

### Agent Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/agent/estimate` | Free complexity estimate |
| `POST` | `/api/agent/buy` | Purchase best workflow |
| `POST` | `/api/agent/rate` | Submit quality rating |

### Commerce & Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/visa/purchase-tokens` | Buy tokens via Visa CyberSource |
| `POST` | `/api/visa/payout` | Creator payout via Visa Direct |
| `GET`  | `/api/visa/health` | Visa integration health check |

### Example: Search

```bash
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"task_type": "tax_filing", "state": "ohio", "year": 2024}'
```

---

## Search Algorithm

A 10-step recursive query decomposition algorithm:

```
1. Broad Search       — kNN + BM25 hybrid across workflows index
2. Score Quality      — Claude evaluates match (0-1)
3. If score ≥ 0.85   — Return direct match
4. Decompose          — Claude splits query into 2-8 subtasks
5. Search Subtasks    — Each subtask searched independently
6. Compose DAG        — Merge results into execution plan
7. Score Composite    — Claude evaluates combined plan
8. Compare Plans      — Keep best if improvement ≥ 0.1
9. Recursive Split    — Tree-aware node search on workflows_nodes index
10. Return Best Plan  — Direct match or composite DAG
```

### Hybrid Search Scoring

```
score = 0.7 × cosine_similarity(JINA_embedding) + 0.3 × BM25(text)
```

JINA embeddings capture semantic meaning ("file my taxes" matches "income tax return preparation"), while BM25 catches exact terms ("IT-1040" matches precisely).

---

## Dynamic Pricing

Transparent, value-based pricing tied to actual token savings.

### Formula

```
price = tokens_saved × 0.15 × quality_multiplier
quality_multiplier = 0.7 + (rating / 5.0) × 0.6
```

### Constraints
- **Floor / ceiling**: 50 – 2,000 tokens
- **Market band**: ±30% of median for comparable workflows

### Example

| Workflow | Tokens Saved | Rating | Price | ROI |
|----------|-------------|--------|-------|-----|
| Ohio 2024 IT-1040 | 10,350 | 4.8★ | 1,981 | 522% |
| California Form 540 | 9,715 | 4.9★ | 1,877 | 518% |
| Tokyo Family Trip | 13,140 | 4.7★ | 2,000 | 657% |
| Stripe Invoice Parser | 7,920 | 4.9★ | 1,530 | 518% |

Typical ROI: **500–650%** (5–6.5x return on every token spent).

---

## Privacy Architecture

Two-layer design — PII never leaves the agent.

**Layer 1 — Public** (sent to marketplace for matching):
```json
{
  "task_type": "tax_filing",
  "state": "ohio",
  "income_bracket": "80k-100k"
}
```

**Layer 2 — Private** (stays local, never transmitted):
```json
{
  "name": "John Smith",
  "ssn": "123-45-6789",
  "exact_income": 87432.18
}
```

Workflows are **templates with placeholders**. The agent fills in private data locally after purchase.

The `sanitizer.py` module strips PII (names, SSNs, exact financials, emails, phone numbers) from queries before they reach the marketplace API.

---

## Deployment

### Backend → Render

```yaml
# render.yaml is pre-configured
# Set environment variables in Render dashboard:
#   ANTHROPIC_API_KEY, JINA_API_KEY, ELASTIC_CLOUD_ID, ELASTIC_API_KEY
```

Build: `pip install -r requirements.txt`
Start: `gunicorn api:app`

### Frontend → Vercel

```bash
# vercel.json is pre-configured
# Set environment variable:
#   NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
vercel --prod
```

API requests are proxied to the backend via the `rewrites` in `vercel.json`.

---

## Demo

### Side-by-Side Comparison

```bash
python demo/run_demo.py          # full demo
python demo/run_demo.py --fast   # skip animations
python demo/run_demo.py --json   # export results
```

| Metric | Without archaitools | With archaitools | Delta |
|--------|---------------------|------------------|-------|
| Accuracy | 37.5% | 100% | +62.5pp |
| Tokens | 4,390 | 1,330 | **−70%** |
| Latency | 8.5s | 3.8s | −55% |
| Errors | 4 | 0 | −100% |
| Edge cases caught | 0 | 6 | +6 |

### Agent SDK Demos

```bash
cd agent-sdk
pip install archaitools anthropic rich
export ANTHROPIC_API_KEY=sk-ant-...

python tax_agent.py              # Ohio tax filing
python shopping_agent.py         # Product comparison
python orchestrator_agent.py     # Multi-task chaining
python run_all.py                # All demos with rich output
```

---

## License

MIT

---

*Built at TreeHacks 2026*