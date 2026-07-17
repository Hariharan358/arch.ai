"""
archaitools — SDK for the Mark AI Agent Workflow Marketplace.

Add pre-solved reasoning workflows to any AI agent in 3 lines:

    from archaitools import MarkClient

    mark = MarkClient(api_key="mk_...")
    result = mark.estimate("File Ohio 2024 taxes with W2 and itemized deductions")

Or expose tools directly to your Claude/OpenAI agent:

    from archaitools import MarkTools

    tools = MarkTools(api_key="mk_...")
    tool_definitions = tools.to_anthropic()  # or tools.to_openai()
"""

from archaitools.client import MarkClient
from archaitools.tools import MarkTools
from archaitools.models import (
    Workflow,
    Solution,
    EstimateResult,
    PurchaseReceipt,
    RateResult,
    SearchResult,
    Subtask,
)
from archaitools.exceptions import (
    MarkError,
    AuthenticationError,
    InsufficientCreditsError,
    WorkflowNotFoundError,
    RateLimitError,
    ServerError,
)

__version__ = "1.0.0"
__all__ = [
    # Core
    "MarkClient",
    "MarkTools",
    # Models
    "Workflow",
    "Solution",
    "EstimateResult",
    "PurchaseReceipt",
    "RateResult",
    "SearchResult",
    "Subtask",
    # Errors
    "MarkError",
    "AuthenticationError",
    "InsufficientCreditsError",
    "WorkflowNotFoundError",
    "RateLimitError",
    "ServerError",
]
