"""
Pydantic models for the archaitools SDK.

These models provide typed, validated representations of all API responses.
They mirror the backend models.py but are designed for SDK consumers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# Core data models
# ──────────────────────────────────────────────────────────────────────────────


class TokenComparison(BaseModel):
    """Token usage comparison: with workflow vs from scratch."""

    with_workflow: int = 0
    from_scratch: int = 0

    @property
    def savings(self) -> int:
        return self.from_scratch - self.with_workflow

    @property
    def savings_percentage(self) -> float:
        if self.from_scratch == 0:
            return 0.0
        return round((self.savings / self.from_scratch) * 100, 1)


class WorkflowStep(BaseModel):
    """A single step in a workflow execution template."""

    step: int = 0
    thought: str = ""
    action: str = ""
    query: Optional[str] = None
    extract: Optional[str] = None
    validation: Optional[str] = None
    edge_case: Optional[str] = None
    formula: Optional[str] = None
    context: Optional[str] = None

    model_config = {"extra": "allow"}


class Workflow(BaseModel):
    """
    A reusable workflow template from the Mark marketplace.

    Workflows contain step-by-step instructions, edge cases, and domain
    knowledge that help AI agents solve tasks more efficiently.
    """

    workflow_id: str
    title: str
    description: str = ""
    task_type: str = "general"

    # Pricing
    download_cost: int = Field(0, description="Cost to download (charged once)")
    execution_cost: int = Field(0, description="Cost to execute (charged per run)")
    token_cost: Optional[int] = Field(None, description="Legacy: alias for download_cost")

    # Metadata
    state: Optional[str] = None
    location: Optional[str] = None
    year: Optional[int] = None
    duration_days: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    rating: float = 0.0
    usage_count: int = 0
    similarity_score: float = 0.0

    # Content
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    edge_cases: List[Any] = Field(default_factory=list)
    domain_knowledge: List[Any] = Field(default_factory=list)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    token_comparison: Optional[TokenComparison] = None

    model_config = {"extra": "allow"}

    @property
    def total_cost(self) -> int:
        """Total cost = download + execution."""
        dl = self.download_cost or self.token_cost or 0
        return dl + self.execution_cost

    @property
    def num_steps(self) -> int:
        return len(self.steps)

    def get_steps(self) -> List[WorkflowStep]:
        """Parse steps into typed WorkflowStep objects."""
        return [WorkflowStep(**s) for s in self.steps]


class Subtask(BaseModel):
    """A decomposed subtask from query analysis."""

    text: str
    task_type: str = "general"
    weight: float = 1.0
    rationale: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# API response models
# ──────────────────────────────────────────────────────────────────────────────


class SearchResult(BaseModel):
    """A single workflow result from search."""

    workflow: Workflow
    score: float = 0.0
    match_percentage: int = 0


class SolutionPricing(BaseModel):
    """Pricing breakdown for a solution."""

    total_cost_tokens: int = 0
    download_cost: int = 0
    execution_cost: int = 0
    from_scratch_estimate: int = 0
    savings_tokens: int = 0
    savings_percentage: int = 0


class SolutionStructure(BaseModel):
    """Structure metadata for a solution."""

    num_workflows: int = 0
    num_subtasks: int = 0
    coverage: str = ""
    execution_order: List[str] = Field(default_factory=list)


class WorkflowSummary(BaseModel):
    """Brief summary of a workflow in a solution."""

    workflow_id: str
    workflow_title: str = ""
    task_type: str = "general"
    subtask_description: str = ""
    token_cost: int = 0


class Solution(BaseModel):
    """
    A ranked solution candidate from the estimate endpoint.

    Each solution is a different combination of workflows that can solve
    the user's task. The agent reviews pricing and picks the best one.
    """

    solution_id: str
    rank: int = 1
    confidence_score: float = 0.0
    pricing: SolutionPricing = Field(default_factory=SolutionPricing)
    structure: SolutionStructure = Field(default_factory=SolutionStructure)
    workflows_summary: List[WorkflowSummary] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class EstimateResult(BaseModel):
    """
    Response from the estimate endpoint.

    Contains multiple ranked solutions the agent can choose from,
    along with query decomposition details and a session_id for purchasing.
    """

    session_id: str = ""
    num_solutions: int = 0
    solutions: List[Solution] = Field(default_factory=list)
    decomposition: Dict[str, Any] = Field(default_factory=dict)
    query: Dict[str, Any] = Field(default_factory=dict)

    @property
    def best_solution(self) -> Optional[Solution]:
        """Get the highest-ranked solution."""
        if not self.solutions:
            return None
        return min(self.solutions, key=lambda s: s.rank)

    @property
    def cheapest_solution(self) -> Optional[Solution]:
        """Get the cheapest solution."""
        if not self.solutions:
            return None
        return min(self.solutions, key=lambda s: s.pricing.total_cost_tokens)


class ExecutionWorkflow(BaseModel):
    """A workflow in a purchased execution plan with full details."""

    subtask_id: str = ""
    description: str = ""
    workflow_id: str = ""
    workflow_title: str = ""
    dependencies: List[str] = Field(default_factory=list)
    children: List[str] = Field(default_factory=list)
    workflow: Workflow = Field(default_factory=lambda: Workflow(workflow_id="", title=""))
    tokens_charged: int = 0


class ExecutionPlan(BaseModel):
    """The full execution plan received after purchase."""

    execution_order: List[str] = Field(default_factory=list)
    root_ids: List[str] = Field(default_factory=list)
    workflows: List[ExecutionWorkflow] = Field(default_factory=list)


class PurchaseReceipt(BaseModel):
    """
    Receipt from purchasing a solution.

    Contains the full execution plan with all workflow details,
    steps, edge cases, and domain knowledge.
    """

    purchase_id: str = ""
    session_id: str = ""
    solution_id: str = ""
    timestamp: str = ""
    tokens_charged: int = 0
    num_workflows: int = 0
    execution_plan: ExecutionPlan = Field(default_factory=ExecutionPlan)
    status: str = "purchased"
    usage_instructions: Dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class RateResult(BaseModel):
    """Response from rating a workflow."""

    workflow_id: str = ""
    new_rating: float = 0.0
    success: bool = False


class BalanceInfo(BaseModel):
    """User balance information."""

    user_id: str = ""
    balance: int = 0


class HealthStatus(BaseModel):
    """API health status."""

    status: str = "unknown"
    timestamp: str = ""
    workflows_loaded: int = 0
    elasticsearch: bool = False
    agent_enabled: bool = False
    orchestrator_enabled: bool = False
