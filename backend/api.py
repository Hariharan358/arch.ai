"""
Main Flask API for the Agent Workflow Marketplace.

Endpoints:
  ── Core Marketplace ──
  GET  /health                   Health check
  GET  /api/workflows            List all workflows
  POST /api/search               Hybrid search (Elastic kNN + BM25)
  POST /api/purchase             Purchase a workflow
  POST /api/feedback             Rate a workflow

  ── Privacy ──
  POST /api/sanitize             Demo PII sanitization

  ── Claude Agent ──
  POST /api/agent/chat           Multi-turn agent conversation
  GET  /api/agent/session        Get session state
  POST /api/agent/reset          Reset agent session

  ── Commerce ──
  GET  /api/commerce/balance     Get user balance
  POST /api/commerce/deposit     Add credits
  POST /api/commerce/cart/add    Add workflow to cart
  POST /api/commerce/cart/remove Remove from cart
  GET  /api/commerce/cart        View cart
  POST /api/commerce/checkout    Checkout cart
  GET  /api/commerce/transactions Transaction history
  GET  /api/commerce/stats       Marketplace statistics

  ── Pricing / Orchestrator (from price-model) ──
  POST /api/estimate             Estimate pricing and search (no purchase)
  POST /api/buy                  Purchase solution and get execution plan
  GET  /api/pricing/<workflow_id> Detailed pricing breakdown

  ── SDK ──
  GET  /api/sdk/info             SDK package info for pip install marktools
  GET  /api/sdk/tools            Tool definitions (Anthropic/OpenAI format)
  GET  /api/sdk/examples         Usage examples

Tech stack: Flask, Elasticsearch, JINA embeddings, Claude Agent SDK
"""

import os
import sys
import json
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sanitizer import PrivacySanitizer
from commerce import CommerceEngine

# Try to import Visa payments (optional, requires Visa credentials)
try:
    from visa_payments import visa_bp
    visa_enabled = True
    print("[api] Visa payment integration loaded")
except Exception as e:
    visa_enabled = False
    print(f"[api] Visa payments disabled ({e})")

# ---------------------------------------------------------------------------
# Try to initialize Elasticsearch + JINA (graceful fallback if keys missing)
# ---------------------------------------------------------------------------
elastic_client = None
try:
    cloud_id = os.getenv("ELASTIC_CLOUD_ID", "")
    api_key = os.getenv("ELASTIC_API_KEY", "")
    jina_key = os.getenv("JINA_API_KEY", "")

    if cloud_id and api_key and jina_key:
        from elastic_client import ElasticClient, JinaEmbedder

        embedder = JinaEmbedder(api_key=jina_key)
        elastic_client = ElasticClient(
            cloud_id=cloud_id, api_key=api_key, jina_embedder=embedder
        )
        print("[api] Elasticsearch + JINA connected")
    else:
        print("[api] Elastic/JINA keys not set — running in-memory fallback mode")
except Exception as e:
    print(f"[api] Elasticsearch init failed ({e}) — using in-memory fallback")

# ---------------------------------------------------------------------------
# Initialize services
# ---------------------------------------------------------------------------
from matcher import WorkflowMatcher

matcher = WorkflowMatcher(elastic_client=elastic_client)
sanitizer = PrivacySanitizer()
commerce = CommerceEngine()

# Load workflows from disk (always, for fallback + listing)
WORKFLOWS_PATH = os.path.join(os.path.dirname(__file__), "workflows.json")
matcher.load_workflows(WORKFLOWS_PATH)

# ---------------------------------------------------------------------------
# Initialize Claude Agent
# ---------------------------------------------------------------------------
agent_instance = None
try:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        from agent import MarketplaceAgent

        agent_instance = MarketplaceAgent(
            elastic_client=elastic_client,
            sanitizer=sanitizer,
            anthropic_api_key=anthropic_key,
        )
        print("[api] Claude Agent initialized")
    else:
        print("[api] ANTHROPIC_API_KEY not set — agent endpoints disabled")
except Exception as e:
    print(f"[api] Agent init failed ({e}) — agent endpoints disabled")

# ---------------------------------------------------------------------------
# Initialize Price-Model Orchestrator (optional — from price-model branch)
# ---------------------------------------------------------------------------
orchestrator = None
try:
    from config import initialize_services
    from orchestrator import MarketplaceOrchestrator

    initialize_services()
    orchestrator = MarketplaceOrchestrator()

    try:
        orchestrator.decomposer.es_service.create_index(delete_existing=False)
    except Exception:
        pass
    try:
        orchestrator.decomposer.load_and_index_workflows("workflows.json")
    except Exception:
        pass

    print("[api] Price-model orchestrator initialized")
except Exception as e:
    print(f"[api] Orchestrator init skipped ({e}) — estimate/buy endpoints disabled")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# Register Visa payments blueprint if enabled
if visa_enabled:
    app.register_blueprint(visa_bp)


# ===== HEALTH =====

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "workflows_loaded": len(matcher.workflows),
        "elasticsearch": elastic_client is not None,
        "agent_enabled": agent_instance is not None,
        "orchestrator_enabled": orchestrator is not None,
        "visa_payments_enabled": visa_enabled,
    })


# ===== CORE MARKETPLACE =====

@app.route("/api/workflows", methods=["GET"])
def list_workflows():
    from pricing import PricingEngine
    workflows = matcher.get_all_workflows()

    # Add dynamic pricing calculation for ALL workflows
    for workflow in workflows:
        rating = workflow.get('rating', 4.0)

        # Derive avg_tokens_without / avg_tokens_with if missing
        # Use execution_tokens as avg_tokens_with (tokens used WITH the workflow)
        # Estimate avg_tokens_without as ~3.2× execution_tokens (observed ratio)
        if 'avg_tokens_with' not in workflow:
            execution_tokens = workflow.get('execution_tokens', 0)
            if execution_tokens > 0:
                workflow['avg_tokens_with'] = execution_tokens
            else:
                workflow['avg_tokens_with'] = 0

        if 'avg_tokens_without' not in workflow:
            avg_with = workflow.get('avg_tokens_with', 0)
            if avg_with > 0:
                workflow['avg_tokens_without'] = int(avg_with * 3.2)
            else:
                workflow['avg_tokens_without'] = 0

        avg_without = workflow.get('avg_tokens_without', 0)
        avg_with = workflow.get('avg_tokens_with', 0)

        # Calculate tokens saved
        tokens_saved = max(0, avg_without - avg_with)
        workflow['tokens_saved'] = tokens_saved

        # Calculate savings percentage
        if avg_without > 0:
            workflow['savings_percentage'] = int((tokens_saved / avg_without) * 100)
        else:
            workflow['savings_percentage'] = 0

        # Calculate pricing via PricingEngine
        if tokens_saved > 0:
            pricing_result = PricingEngine.calculate_workflow_price(
                avg_without,
                avg_with,
                rating,
                None  # No comparable prices for now
            )
            # Use token_cost as price if it exists and no price_tokens set,
            # otherwise use the calculated price
            if 'price_tokens' not in workflow:
                token_cost = workflow.get('token_cost', 0)
                if token_cost > 0:
                    workflow['price_tokens'] = token_cost
                else:
                    workflow['price_tokens'] = pricing_result['final_price']

            # Recalculate ROI with actual price
            actual_price = workflow['price_tokens']
            actual_roi = round((tokens_saved / actual_price * 100), 1) if actual_price > 0 else 0

            workflow['pricing'] = {
                'base_price': pricing_result['base_price'],
                'quality_multiplier': round(pricing_result['quality_multiplier'], 3),
                'market_rate': pricing_result['market_rate'],
                'roi_percentage': actual_roi,
                'breakdown': pricing_result['breakdown']
            }
        else:
            # Fallback for workflows with no savings data
            token_cost = workflow.get('token_cost', 0)
            if 'price_tokens' not in workflow:
                workflow['price_tokens'] = token_cost
            workflow.setdefault('pricing', {
                'base_price': token_cost,
                'quality_multiplier': 1.0,
                'market_rate': None,
                'roi_percentage': 0,
                'breakdown': 'Flat-rate pricing'
            })

    return jsonify({"workflows": workflows, "count": len(workflows)})


@app.route("/api/search", methods=["POST"])
def search_workflows():
    """
    Hybrid search: Elasticsearch kNN (JINA vectors) + BM25.
    Falls back to in-memory if Elastic not configured.

    Body: { "task_type": "...", "state": "...", ... }
    """
    try:
        query = request.json
        if not query:
            return jsonify({"error": "Request body required"}), 400

        results = matcher.search(query, top_k=10)
        return jsonify({"results": results, "count": len(results), "query": query})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/purchase", methods=["POST"])
def purchase_workflow():
    """Purchase a workflow. Deducts tokens, returns full execution template."""
    try:
        data = request.json or {}
        workflow_id = data.get("workflow_id")
        user_id = data.get("user_id", "default_user")

        if not workflow_id:
            return jsonify({"error": "Missing workflow_id"}), 400

        workflow = matcher.get_workflow_by_id(workflow_id)
        if not workflow:
            return jsonify({"error": "Workflow not found"}), 404

        # Process purchase through commerce engine
        receipt = commerce.purchase_workflow(user_id, workflow)
        if not receipt["success"]:
            return jsonify(receipt), 402  # Payment Required

        return jsonify({
            "workflow": workflow,
            "receipt": receipt,
            "purchased_at": datetime.now().isoformat(),
            "success": True,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
def rate_workflow():
    """Rate a workflow (1-5 stars or up/down vote)."""
    try:
        data = request.json or {}
        workflow_id = data.get("workflow_id")
        if not workflow_id:
            return jsonify({"error": "Missing workflow_id"}), 400

        workflow = matcher.get_workflow_by_id(workflow_id)
        if not workflow:
            return jsonify({"error": "Workflow not found"}), 404

        if "rating" in data:
            new_val = data["rating"]
            old = workflow.get("rating", 5.0)
            workflow["rating"] = round((old + new_val) / 2, 1)
        elif "vote" in data:
            if data["vote"] == "up":
                workflow["rating"] = min(5.0, workflow.get("rating", 5.0) + 0.1)
            elif data["vote"] == "down":
                workflow["rating"] = max(1.0, workflow.get("rating", 5.0) - 0.1)

        # Persist to Elastic if available
        if elastic_client:
            try:
                elastic_client.update_field(workflow_id, "rating", workflow["rating"])
            except Exception:
                pass

        return jsonify({
            "workflow_id": workflow_id,
            "new_rating": workflow["rating"],
            "new_usage_count": workflow.get("usage_count", 0),
            "success": True,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===== PRIVACY =====

@app.route("/api/sanitize", methods=["POST"])
def sanitize_query():
    """Demonstrate the two-layer privacy architecture."""
    try:
        data = request.json or {}
        raw_query = data.get("raw_query", {})
        if not raw_query:
            return jsonify({"error": "Missing raw_query"}), 400

        public_query, private_data = sanitizer.sanitize_query(raw_query)
        summary = sanitizer.get_sanitization_summary(raw_query, public_query)

        return jsonify({
            "public_query": public_query,
            "private_data": private_data,
            "sanitization_summary": summary,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===== CLAUDE AGENT =====

@app.route("/api/agent/chat", methods=["POST"])
def agent_chat():
    """
    Multi-turn conversation with the Claude-powered agent.
    The agent autonomously searches, evaluates, purchases, and executes workflows.

    Body: { "message": "Help me file my Ohio taxes" }
    """
    if not agent_instance:
        return jsonify({
            "error": "Agent not configured. Set ANTHROPIC_API_KEY in .env",
        }), 503

    try:
        data = request.json or {}
        message = data.get("message", "")
        if not message:
            return jsonify({"error": "Missing message"}), 400

        result = agent_instance.chat(message)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agent/session", methods=["GET"])
def agent_session():
    """Get current agent session state."""
    if not agent_instance:
        return jsonify({"error": "Agent not configured"}), 503
    return jsonify(agent_instance.get_session_summary())


@app.route("/api/agent/reset", methods=["POST"])
def agent_reset():
    """Reset the agent session (new conversation)."""
    if not agent_instance:
        return jsonify({"error": "Agent not configured"}), 503
    agent_instance.reset_session()
    return jsonify({"success": True, "message": "Session reset"})


# ===== COMMERCE =====

@app.route("/api/commerce/balance", methods=["GET"])
def get_balance():
    user_id = request.args.get("user_id", "default_user")
    return jsonify({"user_id": user_id, "balance": commerce.get_balance(user_id)})


@app.route("/api/commerce/deposit", methods=["POST"])
def deposit_credits():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    amount = data.get("amount", 0)
    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400
    return jsonify(commerce.deposit(user_id, amount))


@app.route("/api/commerce/cart", methods=["GET"])
def view_cart():
    user_id = request.args.get("user_id", "default_user")
    cart = commerce.get_cart(user_id)
    return jsonify(cart.to_dict())


@app.route("/api/commerce/cart/add", methods=["POST"])
def add_to_cart():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    workflow_id = data.get("workflow_id")
    if not workflow_id:
        return jsonify({"error": "Missing workflow_id"}), 400

    workflow = matcher.get_workflow_by_id(workflow_id)
    if not workflow:
        return jsonify({"error": "Workflow not found"}), 404

    return jsonify(commerce.add_to_cart(user_id, workflow))


@app.route("/api/commerce/cart/remove", methods=["POST"])
def remove_from_cart():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    workflow_id = data.get("workflow_id")
    if not workflow_id:
        return jsonify({"error": "Missing workflow_id"}), 400
    return jsonify(commerce.remove_from_cart(user_id, workflow_id))


@app.route("/api/commerce/checkout", methods=["POST"])
def checkout():
    """Checkout all items in the shopping cart."""
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    return jsonify(commerce.checkout_cart(user_id))


@app.route("/api/commerce/transactions", methods=["GET"])
def get_transactions():
    user_id = request.args.get("user_id")
    limit = int(request.args.get("limit", 50))
    return jsonify({
        "transactions": commerce.get_transactions(user_id, limit),
    })


@app.route("/api/commerce/stats", methods=["GET"])
def marketplace_stats():
    return jsonify(commerce.get_marketplace_stats())


# ===== PRICE-MODEL ORCHESTRATOR ENDPOINTS =====

@app.route("/api/estimate", methods=["POST"])
def estimate_price_and_search():
    """
    Estimate pricing and search for solutions (no purchase).
    Requires the price-model orchestrator to be initialized.

    Body: { "query": "...", "context": {...}, "top_k": 5 }
    """
    if not orchestrator:
        return jsonify({
            "error": "Orchestrator not configured. Ensure config.py and orchestrator.py are present.",
        }), 503

    try:
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "Missing 'query' field in request body"}), 400

        query = data["query"]
        context = data.get("context", None)
        top_k = data.get("top_k", 5)

        response = orchestrator.estimate_price_and_search(
            raw_query=query, raw_context=context, top_k=top_k
        )
        return jsonify(response)

    except Exception as e:
        print(f"ERROR in /api/estimate: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "type": "internal_server_error"}), 500


@app.route("/api/buy", methods=["POST"])
def buy_solution():
    """
    Purchase solution and get execution plan.
    Requires the price-model orchestrator to be initialized.

    Body: { "session_id": "...", "solution_id": "sol_1" }
    """
    if not orchestrator:
        return jsonify({
            "error": "Orchestrator not configured. Ensure config.py and orchestrator.py are present.",
        }), 503

    try:
        data = request.get_json()
        if not data or "session_id" not in data or "solution_id" not in data:
            return jsonify({"error": "Missing 'session_id' or 'solution_id'"}), 400

        session_id = data["session_id"]
        solution_id = data["solution_id"]

        purchase = orchestrator.buy_solution(
            session_id=session_id, solution_id=solution_id
        )
        return jsonify(purchase)

    except Exception as e:
        print(f"ERROR in /api/buy: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "type": "internal_server_error"}), 500


@app.route("/api/pricing/<workflow_id>", methods=["GET"])
def get_workflow_pricing(workflow_id):
    """Get detailed pricing breakdown for a specific workflow."""
    try:
        workflow = matcher.get_workflow_by_id(workflow_id)
        if not workflow:
            return jsonify({"error": "Workflow not found"}), 404

        pricing_info = {
            "workflow_id": workflow["workflow_id"],
            "title": workflow["title"],
            "price_tokens": workflow.get("price_tokens", 0),
            "tokens_saved": workflow.get("tokens_saved", 0),
            "savings_percentage": workflow.get("savings_percentage", 0),
            "roi_percentage": workflow.get("pricing", {}).get("roi_percentage", 0),
            "pricing": workflow.get("pricing", {}),
            "avg_tokens_without": workflow.get("avg_tokens_without", 0),
            "avg_tokens_with": workflow.get("avg_tokens_with", 0),
            "rating": workflow.get("rating", 0),
            "usage_count": workflow.get("usage_count", 0),
        }
        return jsonify(pricing_info)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===== SDK ENDPOINTS =====

SDK_VERSION = "0.1.0"

# Tool definitions for agents (same schema as marktools package)
SDK_TOOLS = [
    {
        "name": "mark_estimate",
        "description": (
            "Search the Mark AI marketplace for pre-solved reasoning workflows that match "
            "the agent's current task. Returns ranked solutions with pricing, confidence "
            "scores, and estimated token savings. FREE — no credits spent. "
            "Call this first to decide if the marketplace is worth using."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of the task.",
                },
                "context": {
                    "type": "object",
                    "description": "Optional structured metadata (PII auto-sanitized).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "mark_buy",
        "description": (
            "Purchase a solution from the Mark AI marketplace. Requires a session_id from "
            "a prior mark_estimate call. Deducts credits and returns the full execution plan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID from mark_estimate."},
                "solution_id": {"type": "string", "description": "Solution to purchase (e.g., 'sol_1')."},
            },
            "required": ["session_id", "solution_id"],
        },
    },
    {
        "name": "mark_rate",
        "description": (
            "Rate a purchased workflow after use. Provide rating (1-5) or vote (up/down)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "The workflow_id to rate."},
                "rating": {"type": "integer", "description": "Star rating (1-5).", "minimum": 1, "maximum": 5},
                "vote": {"type": "string", "enum": ["up", "down"], "description": "Quick vote."},
            },
            "required": ["workflow_id"],
        },
    },
    {
        "name": "mark_search",
        "description": (
            "Search the Mark AI marketplace for workflows matching criteria. "
            "Uses hybrid Elasticsearch kNN + BM25 search."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query."},
                "task_type": {"type": "string", "description": "Category filter."},
                "state": {"type": "string", "description": "US state filter."},
                "year": {"type": "integer", "description": "Year filter."},
            },
        },
    },
]


@app.route("/api/sdk/info", methods=["GET"])
def sdk_info():
    """SDK package information for pip install archaitools."""
    return jsonify({
        "package": "archaitools",
        "version": SDK_VERSION,
        "install": "pip install archaitools",
        "pypi_url": "https://pypi.org/project/archaitools/",
        "github": "https://github.com/akhaire21/treehacks-2026",
        "docs": "https://docs.mark.ai",
        "description": "SDK for the Mark AI Agent Workflow Marketplace",
        "quick_start": {
            "install": "pip install archaitools",
            "usage": [
                "from archaitools import MarkClient",
                "",
                "mark = MarkClient(api_key='mk_...')",
                "",
                "# Estimate (free)",
                "estimate = mark.estimate('File Ohio 2024 taxes')",
                "",
                "# Buy best solution",
                "receipt = mark.buy(estimate.session_id, estimate.best_solution.solution_id)",
                "",
                "# Rate after use",
                "mark.rate(receipt.execution_plan.workflows[0].workflow_id, rating=5)",
            ],
        },
        "supported_frameworks": {
            "anthropic": "tools = MarkTools().to_anthropic()",
            "openai": "tools = MarkTools().to_openai()",
            "langchain": "tools = MarkTools().to_langchain()",
        },
        "api_base_url": request.host_url.rstrip("/"),
        "tools_count": len(SDK_TOOLS),
    })


@app.route("/api/sdk/tools", methods=["GET"])
def sdk_tools():
    """Get tool definitions in various formats."""
    fmt = request.args.get("format", "anthropic")

    if fmt == "openai":
        openai_tools = []
        for tool in SDK_TOOLS:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            })
        return jsonify({"tools": openai_tools, "format": "openai"})
    else:
        return jsonify({"tools": SDK_TOOLS, "format": "anthropic"})


@app.route("/api/sdk/examples", methods=["GET"])
def sdk_examples():
    """Get usage examples for different frameworks."""
    return jsonify({
        "anthropic_claude": {
            "title": "Use with Anthropic Claude",
            "code": '''from archaitools import MarkTools
from anthropic import Anthropic

mark = MarkTools(api_key="mk_...")
client = Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    tools=mark.to_anthropic(),
    messages=[{"role": "user", "content": "Help me file my Ohio taxes"}],
)

for block in response.content:
    if block.type == "tool_use":
        result = mark.execute(block.name, block.input)''',
        },
        "openai_gpt4": {
            "title": "Use with OpenAI GPT-4",
            "code": '''from archaitools import MarkTools
from openai import OpenAI

mark = MarkTools(api_key="mk_...")
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    tools=mark.to_openai(),
    messages=[{"role": "user", "content": "Help me file my Ohio taxes"}],
)''',
        },
        "direct_client": {
            "title": "Direct Client Usage",
            "code": '''from archaitools import MarkClient

mark = MarkClient(api_key="mk_...")

# One-shot solve
receipt = mark.solve("File Ohio 2024 taxes with W2 and itemized deductions")

for wf in receipt.execution_plan.workflows:
    print(f"Execute: {wf.workflow_title}")
    for step in wf.workflow.steps:
        print(f"  Step {step['step']}: {step['thought']}")''',
        },
    })


# ===== AGENT SDK SIMULATION ENDPOINTS =====

# Pre-built simulation scenarios for frontend replay
# Loaded from agent-sdk/scenarios.py if available, otherwise inline
import importlib.util
_scenarios_path = os.path.join(os.path.dirname(__file__), "..", "agent-sdk", "scenarios.py")
_scenarios_module = None
if os.path.exists(_scenarios_path):
    spec = importlib.util.spec_from_file_location("scenarios", _scenarios_path)
    _scenarios_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_scenarios_module)


@app.route("/api/sdk/scenarios", methods=["GET"])
def sdk_scenarios():
    """List all available agent simulation scenarios."""
    if _scenarios_module:
        return jsonify({"scenarios": _scenarios_module.list_scenarios()})
    return jsonify({"scenarios": []})


# Inline simulation — no external deps needed
def _simulate_inline(scenario):
    """Build a simulation trace from a pre-defined scenario."""
    steps = []
    tools_called = {}
    for i, step_data in enumerate(scenario.get("steps", [])):
        tool_calls = []
        for tc_data in step_data.get("tool_calls", []):
            tool_calls.append({
                "tool_name": tc_data["tool"],
                "tool_input": tc_data["input"],
                "result": json.dumps(tc_data["result"]) if isinstance(tc_data["result"], dict) else tc_data["result"],
                "latency_ms": tc_data.get("latency_ms", 150),
            })
            tools_called[tc_data["tool"]] = tools_called.get(tc_data["tool"], 0) + 1
        steps.append({
            "step_number": i + 1,
            "thinking": step_data["thinking"],
            "tool_calls": tool_calls,
            "latency_ms": step_data.get("latency_ms", 800),
        })
    return {
        "agent_name": scenario.get("title", "mark-agent"),
        "task": scenario["task"],
        "model": "claude-sonnet-4-20250514",
        "steps": steps,
        "final_response": scenario.get("final_response", ""),
        "total_input_tokens": scenario.get("input_tokens", 2500),
        "total_output_tokens": scenario.get("output_tokens", 1800),
        "total_latency_ms": scenario.get("total_latency_ms", 5000),
        "tools_called": tools_called,
        "success": True,
    }


@app.route("/api/sdk/simulate/<scenario_id>", methods=["GET"])
def sdk_simulate(scenario_id):
    """Get a full simulation trace for a scenario."""
    if _scenarios_module:
        scenario = _scenarios_module.get_scenario(scenario_id)
        if scenario:
            return jsonify(_simulate_inline(scenario))
        return jsonify({"error": f"Scenario '{scenario_id}' not found"}), 404
    return jsonify({"error": "Scenarios not loaded"}), 500


# ===== START =====

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5001))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    print()
    print("=" * 60)
    print("  Agent Workflow Marketplace API")
    print("=" * 60)
    print(f"  Workflows loaded : {len(matcher.workflows)}")
    print(f"  Elasticsearch    : {'connected' if elastic_client else 'off (in-memory fallback)'}")
    print(f"  Claude Agent     : {'ready' if agent_instance else 'disabled (no API key)'}")
    print(f"  Orchestrator     : {'ready' if orchestrator else 'disabled'}")
    print(f"  JINA Embeddings  : {'active' if elastic_client else 'off'}")
    print(f"  Commerce Engine  : active")
    print(f"  SDK package      : archaitools v{SDK_VERSION}")
    print(f"  Server           : http://localhost:{port}")
    print()
    print("  Endpoints:")
    print("    POST /api/search          Search workflows (hybrid kNN + BM25)")
    print("    POST /api/purchase        Purchase workflow")
    print("    POST /api/feedback        Rate workflow")
    print("    POST /api/sanitize        Privacy sanitization demo")
    print("    POST /api/agent/chat      Claude multi-turn agent")
    print("    GET  /api/agent/session   Agent session state")
    print("    POST /api/agent/reset     Reset agent")
    print("    GET  /api/commerce/*      Commerce endpoints")
    print("    GET  /api/workflows       List all workflows")
    print("    POST /api/estimate        Estimate pricing (orchestrator)")
    print("    POST /api/buy             Buy solution (orchestrator)")
    print("    GET  /api/pricing/<id>    Pricing breakdown")
    print("    GET  /api/sdk/info        SDK package info")
    print("    GET  /api/sdk/tools       Tool definitions")
    print("    GET  /api/sdk/examples    Usage examples")
    print("    GET  /api/sdk/scenarios   Agent simulation scenarios")
    print("    GET  /api/sdk/simulate/<id> Run agent simulation")
    print("    GET  /health              Health check")
    print("=" * 60)

    app.run(debug=debug, host="0.0.0.0", port=port)
