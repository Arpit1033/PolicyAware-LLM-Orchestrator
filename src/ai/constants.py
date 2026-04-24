# ── AI Agent Constants ────────────────────────────────────────────
'''
    This file serves as the single source of truth for all constants
    used across AI agent tools and orchestration logic.
    Add new agent-level constants defined in this file.
'''

# ── Error Messages ────────────────────────────────────────────────
INVALID_USER_REQUEST = "Invalid request for user."
INVALID_DOCUMENT_REQUEST = "Invalid request for a document detail, try again"
DOCUMENT_NOT_FOUND = "Document not found, try again"

def permission_denied_message(action: str) -> str:
    """Generates a consistent permission denied message for a given action."""
    return f"You do not have permission to {action} documents!"

# ── Document Tool Limits ──────────────────────────────────────────
MAX_DOCUMENT_RESULTS = 25
MAX_MOVIE_RESULTS = 25

# ── Chat API Limits ───────────────────────────────────────────────
MAX_CHAT_MESSAGE_LENGTH = 2000
CHAT_RATE_LIMIT = "10/m"
