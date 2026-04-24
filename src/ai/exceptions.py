"""
Custom exception hierarchy for the AI agent tools layer.
"""
from ai.constants import (
    INVALID_USER_REQUEST,
    INVALID_DOCUMENT_REQUEST,
    DOCUMENT_NOT_FOUND,
    permission_denied_message
)


class DocumentPermissionError(PermissionError):
    """Raised when a Permit.io policy check denies access."""
    def __init__(self, action: str):
        super().__init__(permission_denied_message(action))
        self.action = action


class InvalidUserContextError(ValueError):
    """Raised when the agent config is missing a valid user_id."""
    def __init__(self, message: str = INVALID_USER_REQUEST):
        super().__init__(message)


class DocumentNotFoundError(LookupError):
    """Raised when a requested document does not exist or is inactive."""
    def __init__(self, message: str = DOCUMENT_NOT_FOUND):
        super().__init__(message)


class DocumentOperationError(RuntimeError):
    """Raised for unexpected errors during a document database operation."""
    def __init__(self, message: str = INVALID_DOCUMENT_REQUEST):
        super().__init__(message)
