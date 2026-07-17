"""
Tests for archaitools SDK.
"""

import json
import pytest
import responses
from archaitools import MarkClient, MarkTools
from archaitools.exceptions import (
    AuthenticationError,
    InsufficientCreditsError,
    MarkError,
    ServerError,
    WorkflowNotFoundError,
)
from archaitools.models import (
    EstimateResult,
    HealthStatus,
    PurchaseReceipt,
    RateResult,
    Solution,
    Workflow,
)


BASE_URL = "http://localhost:5001"


@pytest.fixture
def client():
    """Create a MarkClient pointing to test server."""
    return MarkClient(api_key="mk_test_key", base_url=BASE_URL, max_retries=1)


@pytest.fixture
def tools():
    """Create MarkTools pointing to test server."""
    return MarkTools(api_key="mk_test_key", base_url=BASE_URL)


# ──────────────────────────────────────────────────────────────────────────────
# Model tests
# ──────────────────────────────────────────────────────────────────────────────


class TestModels:
    def test_workflow_from_dict(self):
        wf = Workflow(
            workflow_id="test_1",
            title="Test Workflow",
            description="A test",
            task_type="tax_filing",
            download_cost=200,
            execution_cost=800,
            rating=4.8,
            tags=["test", "tax"],
        )
        assert wf.workflow_id == "test_1"
        assert wf.total_cost == 1000
        assert wf.rating == 4.8
        assert "test" in wf.tags

    def test_workflow_legacy_token_cost(self):
        wf = Workflow(
            workflow_id="legacy",
            title="Legacy",
            token_cost=200,
            execution_cost=500,
        )
        assert wf.total_cost == 700

    def test_workflow_steps(self):
        wf = Workflow(
            workflow_id="steps_test",
            title="Steps",
            steps=[
                {"step": 1, "thought": "First", "action": "search"},
                {"step": 2, "thought": "Second", "action": "calculate"},
            ],
        )
        assert wf.num_steps == 2
        typed_steps = wf.get_steps()
        assert typed_steps[0].thought == "First"
        assert typed_steps[1].action == "calculate"

    def test_estimate_result_best_solution(self):
        est = EstimateResult(
            session_id="sess_123",
            num_solutions=2,
            solutions=[
                Solution(solution_id="sol_1", rank=1, confidence_score=0.9),
                Solution(solution_id="sol_2", rank=2, confidence_score=0.7),
            ],
        )
        assert est.best_solution is not None
        assert est.best_solution.solution_id == "sol_1"

    def test_estimate_result_empty(self):
        est = EstimateResult(session_id="sess_empty")
        assert est.best_solution is None
        assert est.cheapest_solution is None

    def test_solution_pricing(self):
        from archaitools.models import SolutionPricing

        pricing = SolutionPricing(
            total_cost_tokens=500,
            from_scratch_estimate=2000,
            savings_tokens=1500,
            savings_percentage=75,
        )
        assert pricing.savings_percentage == 75

    def test_token_comparison(self):
        from archaitools.models import TokenComparison

        tc = TokenComparison(with_workflow=800, from_scratch=3500)
        assert tc.savings == 2700
        assert tc.savings_percentage == 77.1


# ──────────────────────────────────────────────────────────────────────────────
# Client tests (mocked HTTP)
# ──────────────────────────────────────────────────────────────────────────────


class TestClient:
    @responses.activate
    def test_health(self, client):
        responses.add(
            responses.GET,
            f"{BASE_URL}/health",
            json={
                "status": "healthy",
                "timestamp": "2026-02-14T12:00:00",
                "workflows_loaded": 12,
                "elasticsearch": True,
                "agent_enabled": True,
                "orchestrator_enabled": True,
            },
            status=200,
        )
        health = client.health()
        assert isinstance(health, HealthStatus)
        assert health.status == "healthy"
        assert health.workflows_loaded == 12

    @responses.activate
    def test_search(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/api/search",
            json={
                "results": [
                    {
                        "workflow_id": "ohio_w2_2024",
                        "title": "Ohio Tax Filing",
                        "task_type": "tax_filing",
                        "rating": 4.8,
                        "download_cost": 200,
                        "execution_cost": 800,
                    }
                ],
                "count": 1,
            },
            status=200,
        )
        results = client.search(task_type="tax_filing", state="ohio")
        assert len(results) == 1
        assert results[0].workflow_id == "ohio_w2_2024"
        assert results[0].rating == 4.8

    @responses.activate
    def test_list_workflows(self, client):
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/workflows",
            json={
                "workflows": [
                    {"workflow_id": "w1", "title": "W1"},
                    {"workflow_id": "w2", "title": "W2"},
                ],
                "count": 2,
            },
            status=200,
        )
        workflows = client.list_workflows()
        assert len(workflows) == 2

    @responses.activate
    def test_estimate(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/api/estimate",
            json={
                "session_id": "sess_abc123",
                "num_solutions": 1,
                "solutions": [
                    {
                        "solution_id": "sol_1",
                        "rank": 1,
                        "confidence_score": 0.92,
                        "pricing": {
                            "total_cost_tokens": 500,
                            "savings_percentage": 70,
                        },
                    }
                ],
                "decomposition": {"num_subtasks": 2},
                "query": {"sanitized": {"query": "test"}},
            },
            status=200,
        )
        result = client.estimate("test query")
        assert isinstance(result, EstimateResult)
        assert result.session_id == "sess_abc123"
        assert result.best_solution.confidence_score == 0.92

    @responses.activate
    def test_buy(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/api/buy",
            json={
                "purchase_id": "purchase_abc",
                "session_id": "sess_123",
                "solution_id": "sol_1",
                "tokens_charged": 500,
                "num_workflows": 1,
                "execution_plan": {
                    "execution_order": ["subtask_0"],
                    "root_ids": ["subtask_0"],
                    "workflows": [
                        {
                            "subtask_id": "subtask_0",
                            "workflow_id": "ohio_w2",
                            "workflow_title": "Ohio Tax",
                            "workflow": {
                                "workflow_id": "ohio_w2",
                                "title": "Ohio Tax",
                                "steps": [{"step": 1, "thought": "Calculate"}],
                            },
                        }
                    ],
                },
                "status": "purchased",
            },
            status=200,
        )
        receipt = client.buy("sess_123", "sol_1")
        assert isinstance(receipt, PurchaseReceipt)
        assert receipt.purchase_id == "purchase_abc"
        assert receipt.tokens_charged == 500
        assert len(receipt.execution_plan.workflows) == 1

    @responses.activate
    def test_rate(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/api/feedback",
            json={
                "workflow_id": "ohio_w2",
                "new_rating": 4.9,
                "success": True,
            },
            status=200,
        )
        result = client.rate("ohio_w2", rating=5)
        assert isinstance(result, RateResult)
        assert result.success is True
        assert result.new_rating == 4.9

    @responses.activate
    def test_balance(self, client):
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/commerce/balance",
            json={"user_id": "default_user", "balance": 5000},
            status=200,
        )
        info = client.balance()
        assert info.balance == 5000

    @responses.activate
    def test_auth_error(self, client):
        responses.add(
            responses.GET,
            f"{BASE_URL}/health",
            json={"error": "Invalid API key"},
            status=401,
        )
        with pytest.raises(AuthenticationError):
            client.health()

    @responses.activate
    def test_insufficient_credits(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/api/purchase",
            json={"error": "Insufficient balance", "balance": 100, "cost": 500},
            status=402,
        )
        with pytest.raises(InsufficientCreditsError) as exc_info:
            client.purchase("expensive_workflow")
        assert exc_info.value.balance == 100
        assert exc_info.value.cost == 500

    @responses.activate
    def test_not_found(self, client):
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/pricing/nonexistent",
            json={"error": "Workflow not found"},
            status=404,
        )
        with pytest.raises(WorkflowNotFoundError):
            client.get_workflow("nonexistent")

    @responses.activate
    def test_server_error(self, client):
        responses.add(
            responses.POST,
            f"{BASE_URL}/api/search",
            json={"error": "Internal error"},
            status=500,
        )
        with pytest.raises(ServerError):
            client.search(query="test")


# ──────────────────────────────────────────────────────────────────────────────
# Tool tests
# ──────────────────────────────────────────────────────────────────────────────


class TestTools:
    def test_to_anthropic(self, tools):
        defs = tools.to_anthropic()
        assert isinstance(defs, list)
        assert len(defs) == 4  # estimate, buy, rate, search
        names = {d["name"] for d in defs}
        assert "mark_estimate" in names
        assert "mark_buy" in names
        assert "mark_rate" in names
        assert "mark_search" in names

    def test_to_openai(self, tools):
        defs = tools.to_openai()
        assert isinstance(defs, list)
        assert all(d["type"] == "function" for d in defs)
        names = {d["function"]["name"] for d in defs}
        assert "mark_estimate" in names

    def test_to_anthropic_structure(self, tools):
        defs = tools.to_anthropic()
        for d in defs:
            assert "name" in d
            assert "description" in d
            assert "input_schema" in d
            assert d["input_schema"]["type"] == "object"

    def test_to_openai_structure(self, tools):
        defs = tools.to_openai()
        for d in defs:
            assert d["type"] == "function"
            func = d["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func

    def test_exclude_search(self):
        tools = MarkTools(api_key="mk_test", base_url=BASE_URL, include_search=False)
        defs = tools.to_anthropic()
        assert len(defs) == 3  # No search
        names = {d["name"] for d in defs}
        assert "mark_search" not in names

    def test_static_tool_accessors(self):
        est = MarkTools.estimate_tool()
        assert est["name"] == "mark_estimate"

        buy = MarkTools.buy_tool()
        assert buy["name"] == "mark_buy"

        rate = MarkTools.rate_tool()
        assert rate["name"] == "mark_rate"

        search = MarkTools.search_tool()
        assert search["name"] == "mark_search"

    @responses.activate
    def test_execute_estimate(self, tools):
        responses.add(
            responses.POST,
            f"{BASE_URL}/api/estimate",
            json={
                "session_id": "sess_test",
                "num_solutions": 1,
                "solutions": [
                    {
                        "solution_id": "sol_1",
                        "rank": 1,
                        "confidence_score": 0.9,
                        "pricing": {"total_cost_tokens": 300, "savings_percentage": 60},
                        "structure": {"num_workflows": 1},
                        "workflows_summary": [
                            {"workflow_id": "w1", "workflow_title": "Test", "token_cost": 300}
                        ],
                    }
                ],
                "decomposition": {},
            },
            status=200,
        )

        result_str = tools.execute("mark_estimate", {"query": "test"})
        result = json.loads(result_str)
        assert result["session_id"] == "sess_test"
        assert len(result["solutions"]) == 1

    def test_execute_unknown_tool(self, tools):
        result_str = tools.execute("unknown_tool", {})
        result = json.loads(result_str)
        assert "error" in result

    def test_repr(self, tools):
        r = repr(tools)
        assert "MarkTools" in r


# ──────────────────────────────────────────────────────────────────────────────
# Integration tests (against real server, skipped by default)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(True, reason="Requires running backend server")
class TestIntegration:
    def test_full_flow(self):
        mark = MarkClient(base_url="http://localhost:5001")

        # Health
        health = mark.health()
        assert health.status == "healthy"

        # Search
        results = mark.search(task_type="tax_filing")
        assert len(results) > 0

        # Balance
        balance = mark.balance()
        assert balance.balance > 0
