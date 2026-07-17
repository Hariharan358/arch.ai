"""
MarkClient — the core HTTP client for the Mark AI Agent Workflow Marketplace.

Usage:
    from archaitools import MarkClient

    mark = MarkClient(api_key="mk_...")

    # Estimate — free, no credits spent
    estimate = mark.estimate("File Ohio 2024 taxes with W2 and itemized deductions")

    # Buy the best solution
    receipt = mark.buy(estimate.session_id, estimate.best_solution.solution_id)

    # Rate after use
    mark.rate(receipt.execution_plan.workflows[0].workflow_id, rating=5)
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Union

import requests

from archaitools.exceptions import (
    AuthenticationError,
    InsufficientCreditsError,
    MarkError,
    RateLimitError,
    ServerError,
    SessionExpiredError,
    WorkflowNotFoundError,
)
from archaitools.models import (
    BalanceInfo,
    EstimateResult,
    HealthStatus,
    PurchaseReceipt,
    RateResult,
    SearchResult,
    Workflow,
)


_DEFAULT_BASE_URL = "https://api.mark.ai"
_ENV_API_KEY = "MARK_API_KEY"
_ENV_BASE_URL = "MARK_API_URL"

# Retry config
_MAX_RETRIES = 3
_RETRY_BACKOFF = 0.5


class MarkClient:
    """
    HTTP client for the Mark AI Agent Workflow Marketplace.

    Provides typed methods for every API endpoint with automatic
    retry, error handling, and response parsing.

    Args:
        api_key: Your Mark API key (starts with ``mk_``). Falls back to
                 the ``MARK_API_KEY`` environment variable.
        base_url: Override the API base URL. Defaults to ``MARK_API_URL``
                   env var or ``https://api.mark.ai``.
        user_id: User identifier for billing. Defaults to ``"default_user"``.
        timeout: Request timeout in seconds.
        max_retries: Number of retries on transient failures.

    Example::

        from archaitools import MarkClient

        mark = MarkClient()  # uses MARK_API_KEY env var

        # Search workflows
        results = mark.search(task_type="tax_filing", state="ohio")

        # Estimate pricing
        estimate = mark.estimate("File Ohio 2024 taxes")
        print(f"Best solution: {estimate.best_solution.pricing.total_cost_tokens} tokens")

        # Purchase
        receipt = mark.buy(estimate.session_id, estimate.best_solution.solution_id)
        for wf in receipt.execution_plan.workflows:
            print(f"  Execute: {wf.workflow_title}")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        user_id: str = "default_user",
        timeout: int = 30,
        max_retries: int = _MAX_RETRIES,
    ):
        self.api_key = api_key or os.environ.get(_ENV_API_KEY, "")
        self.base_url = (base_url or os.environ.get(_ENV_BASE_URL, _DEFAULT_BASE_URL)).rstrip("/")
        self.user_id = user_id
        self.timeout = timeout
        self.max_retries = max_retries

        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "archaitools-python/0.1.0",
        })
        if self.api_key:
            self._session.headers["Authorization"] = f"Bearer {self.api_key}"

    # ──────────────────────────────────────────────────────────────────────
    # Internal HTTP helpers
    # ──────────────────────────────────────────────────────────────────────

    def _url(self, path: str) -> str:
        """Build full URL from path."""
        return f"{self.base_url}{path}"

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic and error mapping.

        Returns parsed JSON response dict.
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = self._session.request(
                    method=method,
                    url=self._url(path),
                    json=json,
                    params=params,
                    timeout=self.timeout,
                )
                return self._handle_response(response)

            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(_RETRY_BACKOFF * (2 ** attempt))
                    continue
                raise ServerError(
                    f"Connection failed after {self.max_retries} attempts: {e}",
                    status_code=503,
                )

            except MarkError:
                raise  # Don't retry client errors

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(_RETRY_BACKOFF * (2 ** attempt))
                    continue

        raise ServerError(f"Request failed: {last_error}")

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Parse response and raise appropriate errors."""
        try:
            data = response.json()
        except ValueError:
            data = {"error": response.text}

        if response.status_code == 200:
            return data

        error_msg = data.get("error", response.text)

        if response.status_code == 401:
            raise AuthenticationError(error_msg)
        elif response.status_code == 402:
            raise InsufficientCreditsError(
                error_msg,
                balance=data.get("balance", 0),
                cost=data.get("cost", 0),
            )
        elif response.status_code == 404:
            raise WorkflowNotFoundError(data.get("workflow_id", "unknown"))
        elif response.status_code == 410:
            raise SessionExpiredError(data.get("session_id", "unknown"))
        elif response.status_code == 429:
            raise RateLimitError(retry_after=response.headers.get("Retry-After"))
        elif response.status_code >= 500:
            raise ServerError(error_msg, status_code=response.status_code)
        else:
            raise MarkError(error_msg, status_code=response.status_code, response=data)

    # ──────────────────────────────────────────────────────────────────────
    # Health
    # ──────────────────────────────────────────────────────────────────────

    def health(self) -> HealthStatus:
        """
        Check API health status.

        Returns:
            HealthStatus with connectivity info.
        """
        data = self._request("GET", "/health")
        return HealthStatus(**data)

    # ──────────────────────────────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────────────────────────────

    def search(
        self,
        query: Optional[str] = None,
        task_type: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[int] = None,
        location: Optional[str] = None,
        top_k: int = 10,
        **filters: Any,
    ) -> List[Workflow]:
        """
        Search the workflow marketplace using hybrid search (kNN + BM25).

        At least one of ``query`` or ``task_type`` should be provided.

        Args:
            query: Natural language search query.
            task_type: Filter by workflow type (tax_filing, travel_planning, etc.).
            state: Filter by US state.
            year: Filter by year.
            location: Filter by location.
            top_k: Maximum results to return.
            **filters: Additional filters passed to the API.

        Returns:
            List of matching Workflow objects sorted by relevance.

        Example::

            results = mark.search(task_type="tax_filing", state="ohio", year=2024)
            for wf in results:
                print(f"{wf.title} — ★{wf.rating} — ◈{wf.total_cost} tokens")
        """
        body: Dict[str, Any] = {}
        if query:
            body["query"] = query
        if task_type:
            body["task_type"] = task_type
        if state:
            body["state"] = state
        if year:
            body["year"] = year
        if location:
            body["location"] = location
        body.update(filters)

        data = self._request("POST", "/api/search", json=body)
        results = data.get("results", [])
        return [Workflow(**r) for r in results]

    def list_workflows(self) -> List[Workflow]:
        """
        List all available workflows in the marketplace.

        Returns:
            List of all Workflow objects.
        """
        data = self._request("GET", "/api/workflows")
        workflows = data.get("workflows", [])
        return [Workflow(**w) for w in workflows]

    def get_workflow(self, workflow_id: str) -> Workflow:
        """
        Get pricing details for a specific workflow.

        Args:
            workflow_id: The workflow identifier.

        Returns:
            Workflow with pricing info.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
        """
        data = self._request("GET", f"/api/pricing/{workflow_id}")
        return Workflow(**data)

    # ──────────────────────────────────────────────────────────────────────
    # Estimate (Phase 1 — free)
    # ──────────────────────────────────────────────────────────────────────

    def estimate(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> EstimateResult:
        """
        Estimate pricing and search for solutions — **free, no credits spent**.

        This is the primary entry point for agents. It:
        1. Sanitizes PII from the query
        2. Decomposes complex tasks into subtasks
        3. Searches the marketplace using hybrid kNN + BM25
        4. Returns ranked solutions with pricing

        The returned ``session_id`` is used in :meth:`buy` to purchase.

        Args:
            query: Natural language task description.
            context: Optional metadata dict (may contain PII — will be sanitized).
            top_k: Number of solution candidates to generate.

        Returns:
            EstimateResult with ranked solutions and session_id.

        Example::

            estimate = mark.estimate(
                "File Ohio 2024 taxes with W2 and itemized deductions",
                context={"state": "ohio", "year": 2024}
            )
            print(f"Best: {estimate.best_solution.pricing.total_cost_tokens} tokens")
            print(f"Savings: {estimate.best_solution.pricing.savings_percentage}%")
        """
        body: Dict[str, Any] = {"query": query, "top_k": top_k}
        if context:
            body["context"] = context

        data = self._request("POST", "/api/estimate", json=body)
        return EstimateResult(**data)

    # ──────────────────────────────────────────────────────────────────────
    # Buy (Phase 2 — costs credits)
    # ──────────────────────────────────────────────────────────────────────

    def buy(
        self,
        session_id: str,
        solution_id: str,
    ) -> PurchaseReceipt:
        """
        Purchase a solution and receive the full execution plan.

        Requires a ``session_id`` from a prior :meth:`estimate` call.

        Args:
            session_id: Session ID from :meth:`estimate`.
            solution_id: Which solution to buy (e.g., ``"sol_1"``).

        Returns:
            PurchaseReceipt with full workflow details and execution plan.

        Raises:
            InsufficientCreditsError: If balance is too low.
            SessionExpiredError: If the session has expired.

        Example::

            receipt = mark.buy(estimate.session_id, "sol_1")
            for wf in receipt.execution_plan.workflows:
                print(f"Step: {wf.workflow_title}")
                for step in wf.workflow.steps:
                    print(f"  {step.get('step')}: {step.get('thought')}")
        """
        body = {"session_id": session_id, "solution_id": solution_id}
        data = self._request("POST", "/api/buy", json=body)
        return PurchaseReceipt(**data)

    # ──────────────────────────────────────────────────────────────────────
    # Rate
    # ──────────────────────────────────────────────────────────────────────

    def rate(
        self,
        workflow_id: str,
        rating: Optional[int] = None,
        vote: Optional[str] = None,
    ) -> RateResult:
        """
        Rate a workflow after use.

        Provide either a numeric ``rating`` (1–5) or a ``vote`` ("up"/"down").

        Args:
            workflow_id: The workflow to rate.
            rating: Star rating (1–5).
            vote: Quick vote ("up" or "down").

        Returns:
            RateResult with new average rating.

        Example::

            mark.rate("ohio_w2_itemized_2024", rating=5)
            mark.rate("ohio_w2_itemized_2024", vote="up")
        """
        body: Dict[str, Any] = {"workflow_id": workflow_id}
        if rating is not None:
            body["rating"] = rating
        if vote is not None:
            body["vote"] = vote

        data = self._request("POST", "/api/feedback", json=body)
        return RateResult(**data)

    # ──────────────────────────────────────────────────────────────────────
    # Commerce
    # ──────────────────────────────────────────────────────────────────────

    def balance(self) -> BalanceInfo:
        """
        Get current credit balance.

        Returns:
            BalanceInfo with user_id and balance.
        """
        data = self._request("GET", "/api/commerce/balance", params={"user_id": self.user_id})
        return BalanceInfo(**data)

    def deposit(self, amount: int) -> Dict[str, Any]:
        """
        Add credits to your account.

        Args:
            amount: Number of credits to add.

        Returns:
            Dict with new_balance and tx_id.
        """
        return self._request(
            "POST", "/api/commerce/deposit",
            json={"user_id": self.user_id, "amount": amount},
        )

    # ──────────────────────────────────────────────────────────────────────
    # Privacy
    # ──────────────────────────────────────────────────────────────────────

    def sanitize(self, raw_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preview PII sanitization without making a real query.

        Useful for debugging what data gets sent to the marketplace vs. kept local.

        Args:
            raw_query: Dict that may contain PII fields.

        Returns:
            Dict with ``public_query``, ``private_data``, and ``sanitization_summary``.

        Example::

            result = mark.sanitize({
                "name": "John Smith",
                "ssn": "123-45-6789",
                "state": "ohio",
                "exact_income": 87432.18
            })
            print(result["public_query"])    # {'state': 'ohio', 'exact_income': '80k-100k'}
            print(result["private_data"])    # {'name': 'John Smith', 'ssn': '123-45-6789'}
        """
        return self._request("POST", "/api/sanitize", json={"raw_query": raw_query})

    # ──────────────────────────────────────────────────────────────────────
    # Direct purchase (simpler flow, no estimate)
    # ──────────────────────────────────────────────────────────────────────

    def purchase(self, workflow_id: str) -> Dict[str, Any]:
        """
        Purchase a single workflow directly (simpler than estimate → buy).

        Args:
            workflow_id: The workflow to purchase.

        Returns:
            Dict with workflow data and receipt.

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist.
            InsufficientCreditsError: If balance is too low.
        """
        return self._request(
            "POST", "/api/purchase",
            json={"workflow_id": workflow_id, "user_id": self.user_id},
        )

    # ──────────────────────────────────────────────────────────────────────
    # Agent Chat
    # ──────────────────────────────────────────────────────────────────────

    def chat(self, message: str) -> Dict[str, Any]:
        """
        Send a message to the Claude-powered marketplace agent.

        The agent autonomously searches, evaluates, purchases, and
        executes workflows based on the conversation.

        Args:
            message: Natural language message.

        Returns:
            Dict with ``response``, ``tool_calls``, ``session_stats``.
        """
        return self._request(
            "POST", "/api/agent/chat",
            json={"message": message},
        )

    def reset_agent(self) -> Dict[str, Any]:
        """Reset the agent session for a fresh conversation."""
        return self._request("POST", "/api/agent/reset")

    # ──────────────────────────────────────────────────────────────────────
    # Convenience: one-shot solve
    # ──────────────────────────────────────────────────────────────────────

    def solve(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        auto_buy: bool = True,
        max_cost: Optional[int] = None,
    ) -> Union[PurchaseReceipt, EstimateResult]:
        """
        One-shot convenience: estimate + auto-buy the best solution.

        If ``auto_buy`` is True and the best solution is within ``max_cost``,
        automatically purchases and returns the receipt. Otherwise returns
        the estimate for the agent to decide.

        Args:
            query: Task description.
            context: Optional metadata.
            auto_buy: Whether to auto-purchase the best solution.
            max_cost: Maximum tokens to spend (default: no limit).

        Returns:
            PurchaseReceipt if bought, EstimateResult if not.

        Example::

            receipt = mark.solve("File Ohio 2024 taxes")
            if isinstance(receipt, PurchaseReceipt):
                print(f"Purchased! {receipt.tokens_charged} tokens")
        """
        estimate = self.estimate(query, context=context)

        if not estimate.solutions:
            return estimate

        best = estimate.best_solution
        if not best:
            return estimate

        if not auto_buy:
            return estimate

        if max_cost is not None and best.pricing.total_cost_tokens > max_cost:
            return estimate

        return self.buy(estimate.session_id, best.solution_id)

    # ──────────────────────────────────────────────────────────────────────
    # Repr
    # ──────────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        masked_key = f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 10 else "***"
        return f"MarkClient(base_url={self.base_url!r}, api_key={masked_key!r})"
