"""
Custom exceptions for the archaitools SDK.

All exceptions inherit from MarkError so callers can catch
all SDK errors with a single except clause.
"""


class MarkError(Exception):
    """Base exception for all archaitools errors."""

    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r}, status_code={self.status_code})"


class AuthenticationError(MarkError):
    """Raised when the API key is invalid or missing."""

    def __init__(self, message: str = "Invalid or missing API key."):
        super().__init__(message, status_code=401)


class InsufficientCreditsError(MarkError):
    """Raised when the user does not have enough credits to purchase."""

    def __init__(
        self,
        message: str = "Insufficient credits.",
        balance: int = 0,
        cost: int = 0,
    ):
        super().__init__(message, status_code=402)
        self.balance = balance
        self.cost = cost
        self.shortfall = cost - balance


class WorkflowNotFoundError(MarkError):
    """Raised when a workflow_id does not exist."""

    def __init__(self, workflow_id: str):
        super().__init__(f"Workflow '{workflow_id}' not found.", status_code=404)
        self.workflow_id = workflow_id


class RateLimitError(MarkError):
    """Raised when the API rate limit is exceeded."""

    def __init__(self, retry_after: float | None = None):
        msg = "Rate limit exceeded."
        if retry_after:
            msg += f" Retry after {retry_after}s."
        super().__init__(msg, status_code=429)
        self.retry_after = retry_after


class ServerError(MarkError):
    """Raised when the API returns a 5xx error."""

    def __init__(self, message: str = "Internal server error.", status_code: int = 500):
        super().__init__(message, status_code=status_code)


class SessionExpiredError(MarkError):
    """Raised when a session_id from /estimate has expired."""

    def __init__(self, session_id: str):
        super().__init__(
            f"Session '{session_id}' expired or not found. Call estimate() again.",
            status_code=410,
        )
        self.session_id = session_id
