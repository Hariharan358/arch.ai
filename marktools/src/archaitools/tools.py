"""
MarkTools — tool definitions for AI agents.

Provides ready-to-use tool definitions that can be passed to any LLM framework:
- Anthropic Claude (tool_use)
- OpenAI (function calling)
- LangChain (tools)
- Raw JSON schema

Usage with Anthropic::

    from archaitools import MarkTools
    from anthropic import Anthropic

    mark = MarkTools(api_key="mk_...")
    client = Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        tools=mark.to_anthropic(),
        messages=[{"role": "user", "content": "Help me file my Ohio taxes"}],
    )

Usage with OpenAI::

    from archaitools import MarkTools
    from openai import OpenAI

    mark = MarkTools(api_key="mk_...")
    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o",
        tools=mark.to_openai(),
        messages=[{"role": "user", "content": "Help me file my Ohio taxes"}],
    )
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Union

from archaitools.client import MarkClient
from archaitools.models import EstimateResult, PurchaseReceipt, RateResult


# ──────────────────────────────────────────────────────────────────────────────
# Tool definitions (JSON Schema)
# ──────────────────────────────────────────────────────────────────────────────

_TOOL_ESTIMATE = {
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
                "description": (
                    "Natural language description of the task. Be specific — include "
                    "location, year, requirements, and constraints."
                ),
            },
            "context": {
                "type": "object",
                "description": (
                    "Optional structured metadata. Can include PII — it will be "
                    "automatically sanitized before being sent to the marketplace. "
                    "Example: {\"state\": \"ohio\", \"year\": 2024, \"income\": 87000}"
                ),
            },
        },
        "required": ["query"],
    },
}

_TOOL_BUY = {
    "name": "mark_buy",
    "description": (
        "Purchase a solution from the Mark AI marketplace. Requires a session_id from "
        "a prior mark_estimate call. Deducts credits and returns the full execution plan "
        "with step-by-step instructions, edge cases, and domain knowledge. "
        "The agent should review pricing from mark_estimate before calling this."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Session ID returned by mark_estimate.",
            },
            "solution_id": {
                "type": "string",
                "description": (
                    "Which solution to purchase (e.g., 'sol_1'). Choose based on "
                    "cost, confidence, and coverage from mark_estimate results."
                ),
            },
        },
        "required": ["session_id", "solution_id"],
    },
}

_TOOL_RATE = {
    "name": "mark_rate",
    "description": (
        "Rate a purchased workflow after use. Helps improve marketplace quality. "
        "Provide either a numeric rating (1-5 stars) or a quick vote (up/down)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "workflow_id": {
                "type": "string",
                "description": "The workflow_id to rate (from the execution plan).",
            },
            "rating": {
                "type": "integer",
                "description": "Star rating from 1 to 5.",
                "minimum": 1,
                "maximum": 5,
            },
            "vote": {
                "type": "string",
                "enum": ["up", "down"],
                "description": "Quick thumbs up/down vote.",
            },
        },
        "required": ["workflow_id"],
    },
}

_TOOL_SEARCH = {
    "name": "mark_search",
    "description": (
        "Search the Mark AI marketplace for workflows matching specific criteria. "
        "Uses hybrid Elasticsearch kNN + BM25 search. Returns workflow metadata "
        "without purchasing. Useful for browsing or when estimate is overkill."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query.",
            },
            "task_type": {
                "type": "string",
                "description": "Category filter: tax_filing, travel_planning, shopping, etc.",
            },
            "state": {
                "type": "string",
                "description": "US state filter.",
            },
            "year": {
                "type": "integer",
                "description": "Year filter.",
            },
        },
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# MarkTools class
# ──────────────────────────────────────────────────────────────────────────────


class MarkTools:
    """
    Tool definitions + execution for AI agents.

    Wraps the MarkClient and exposes 3 core tools that any agent can call:
    - ``mark_estimate`` — search & price (free)
    - ``mark_buy`` — purchase solution (costs credits)
    - ``mark_rate`` — post-use feedback

    Plus optional:
    - ``mark_search`` — browse the marketplace

    Supports:
    - Anthropic Claude tool_use format
    - OpenAI function calling format
    - LangChain tool format
    - Raw JSON schema

    Args:
        api_key: Mark API key (or set ``MARK_API_KEY`` env var).
        base_url: Override API URL.
        user_id: User ID for billing.
        include_search: Whether to include the mark_search tool.

    Example::

        from archaitools import MarkTools
        from anthropic import Anthropic

        tools = MarkTools(api_key="mk_...")

        # Pass to Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            tools=tools.to_anthropic(),
            messages=[...],
        )

        # Execute tool calls
        for block in response.content:
            if block.type == "tool_use":
                result = tools.execute(block.name, block.input)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        user_id: str = "default_user",
        include_search: bool = True,
    ):
        self.client = MarkClient(
            api_key=api_key,
            base_url=base_url,
            user_id=user_id,
        )
        self._include_search = include_search

        # Map tool names to handler functions
        self._handlers: Dict[str, Callable[..., Any]] = {
            "mark_estimate": self._handle_estimate,
            "mark_buy": self._handle_buy,
            "mark_rate": self._handle_rate,
            "mark_search": self._handle_search,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Tool definitions in various formats
    # ──────────────────────────────────────────────────────────────────────

    def _core_tools(self) -> List[Dict[str, Any]]:
        """Get the list of tool definitions."""
        tools = [_TOOL_ESTIMATE, _TOOL_BUY, _TOOL_RATE]
        if self._include_search:
            tools.append(_TOOL_SEARCH)
        return tools

    def to_anthropic(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions in Anthropic Claude ``tool_use`` format.

        Returns:
            List of tool dicts ready for ``client.messages.create(tools=...)``.

        Example::

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                tools=mark.to_anthropic(),
                messages=[...],
            )
        """
        return self._core_tools()

    def to_openai(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions in OpenAI function calling format.

        Returns:
            List of tool dicts ready for ``client.chat.completions.create(tools=...)``.

        Example::

            response = client.chat.completions.create(
                model="gpt-4o",
                tools=mark.to_openai(),
                messages=[...],
            )
        """
        openai_tools = []
        for tool in self._core_tools():
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            })
        return openai_tools

    def to_langchain(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions compatible with LangChain.

        Returns:
            List of tool dicts for LangChain's StructuredTool.from_function.
        """
        return self.to_openai()  # LangChain uses the same format as OpenAI

    def to_json_schema(self) -> List[Dict[str, Any]]:
        """
        Get raw JSON Schema tool definitions.

        Returns:
            List of tool dicts with name, description, and input_schema.
        """
        return self._core_tools()

    # ──────────────────────────────────────────────────────────────────────
    # Tool execution
    # ──────────────────────────────────────────────────────────────────────

    def execute(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> str:
        """
        Execute a tool call and return the JSON result string.

        This is the bridge between LLM tool_use and the Mark API.
        Pass the tool name and input from the LLM response, get back
        a JSON string to return as tool_result.

        Args:
            tool_name: Name of the tool (e.g., ``"mark_estimate"``).
            tool_input: Input dict from the LLM.

        Returns:
            JSON string with the result.

        Example (Anthropic)::

            for block in response.content:
                if block.type == "tool_use":
                    result = tools.execute(block.name, block.input)
                    # Return result to Claude as tool_result
        """
        handler = self._handlers.get(tool_name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        try:
            result = handler(tool_input)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "tool": tool_name})

    # ──────────────────────────────────────────────────────────────────────
    # Individual tool handlers
    # ──────────────────────────────────────────────────────────────────────

    def _handle_estimate(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        """Handle mark_estimate tool call."""
        query = inp.get("query", "")
        context = inp.get("context")

        estimate = self.client.estimate(query, context=context)

        # Return a summary that's useful for the agent
        solutions_summary = []
        for sol in estimate.solutions:
            solutions_summary.append({
                "solution_id": sol.solution_id,
                "rank": sol.rank,
                "confidence": sol.confidence_score,
                "total_cost_tokens": sol.pricing.total_cost_tokens,
                "savings_percentage": sol.pricing.savings_percentage,
                "num_workflows": sol.structure.num_workflows,
                "workflows": [
                    {"id": w.workflow_id, "title": w.workflow_title, "cost": w.token_cost}
                    for w in sol.workflows_summary
                ],
            })

        return {
            "session_id": estimate.session_id,
            "num_solutions": estimate.num_solutions,
            "solutions": solutions_summary,
            "decomposition": estimate.decomposition,
        }

    def _handle_buy(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        """Handle mark_buy tool call."""
        session_id = inp["session_id"]
        solution_id = inp["solution_id"]

        receipt = self.client.buy(session_id, solution_id)

        # Return execution plan summary
        workflows = []
        for wf in receipt.execution_plan.workflows:
            workflows.append({
                "workflow_id": wf.workflow_id,
                "title": wf.workflow_title,
                "description": wf.description,
                "num_steps": len(wf.workflow.steps),
                "steps_preview": wf.workflow.steps[:5],
                "edge_cases": wf.workflow.edge_cases[:3] if wf.workflow.edge_cases else [],
                "domain_knowledge": wf.workflow.domain_knowledge[:3] if wf.workflow.domain_knowledge else [],
            })

        return {
            "purchase_id": receipt.purchase_id,
            "tokens_charged": receipt.tokens_charged,
            "execution_order": receipt.execution_plan.execution_order,
            "workflows": workflows,
            "status": receipt.status,
        }

    def _handle_rate(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        """Handle mark_rate tool call."""
        workflow_id = inp["workflow_id"]
        rating = inp.get("rating")
        vote = inp.get("vote")

        result = self.client.rate(workflow_id, rating=rating, vote=vote)
        return {
            "success": result.success,
            "workflow_id": result.workflow_id,
            "new_rating": result.new_rating,
        }

    def _handle_search(self, inp: Dict[str, Any]) -> Dict[str, Any]:
        """Handle mark_search tool call."""
        workflows = self.client.search(
            query=inp.get("query"),
            task_type=inp.get("task_type"),
            state=inp.get("state"),
            year=inp.get("year"),
        )

        results = []
        for wf in workflows[:10]:
            results.append({
                "workflow_id": wf.workflow_id,
                "title": wf.title,
                "description": wf.description[:200] if wf.description else "",
                "task_type": wf.task_type,
                "rating": wf.rating,
                "usage_count": wf.usage_count,
                "total_cost": wf.total_cost,
                "tags": wf.tags,
            })

        return {"results": results, "count": len(results)}

    # ──────────────────────────────────────────────────────────────────────
    # Convenience: individual tool accessors
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def estimate_tool() -> Dict[str, Any]:
        """Get just the mark_estimate tool definition."""
        return _TOOL_ESTIMATE

    @staticmethod
    def buy_tool() -> Dict[str, Any]:
        """Get just the mark_buy tool definition."""
        return _TOOL_BUY

    @staticmethod
    def rate_tool() -> Dict[str, Any]:
        """Get just the mark_rate tool definition."""
        return _TOOL_RATE

    @staticmethod
    def search_tool() -> Dict[str, Any]:
        """Get just the mark_search tool definition."""
        return _TOOL_SEARCH

    def __repr__(self) -> str:
        n = len(self._core_tools())
        return f"MarkTools(tools={n}, client={self.client!r})"
