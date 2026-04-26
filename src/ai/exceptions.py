"""
Custom exception hierarchy for the AI agent tools layer.

All tool-level exceptions inherit from AgentToolError, which carries
its own HTTP status_code and log_level. The API layer catches the base
class once — no new except blocks needed when adding future tools.
"""
import logging
from ai.constants import (
    INVALID_USER_REQUEST,
    INVALID_DOCUMENT_REQUEST,
    DOCUMENT_NOT_FOUND,
    permission_denied_message
)


class AgentToolError(Exception):
    """
    Base exception for all AI agent tool errors.

    Subclasses set `status_code` and `log_level` so the API endpoint
    can handle every tool error with a single except block.
    """
    status_code: int = 500
    log_level: int = logging.ERROR

    def __init__(self, message: str):
        super().__init__(message)


class DocumentPermissionError(AgentToolError):
    """Raised when a Permit.io policy check denies access."""
    status_code = 403
    log_level = logging.WARNING

    def __init__(self, action: str):
        super().__init__(permission_denied_message(action))
        self.action = action


class InvalidUserContextError(AgentToolError):
    """Raised when the agent config is missing a valid user_id."""
    status_code = 400
    log_level = logging.WARNING

    def __init__(self, message: str = INVALID_USER_REQUEST):
        super().__init__(message)


class DocumentNotFoundError(AgentToolError):
    """Raised when a requested document does not exist or is inactive."""
    status_code = 404
    log_level = logging.WARNING

    def __init__(self, message: str = DOCUMENT_NOT_FOUND):
        super().__init__(message)


class DocumentOperationError(AgentToolError):
    """Raised for unexpected errors during a document database operation."""
    status_code = 422
    log_level = logging.ERROR

    def __init__(self, message: str = INVALID_DOCUMENT_REQUEST):
        super().__init__(message)
