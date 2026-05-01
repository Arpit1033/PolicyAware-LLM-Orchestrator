from ninja import Router, Schema
from langchain_core.messages import HumanMessage
from ai.checkpointer import get_checkpointer
from ninja.errors import HttpError
from google.api_core.exceptions import ResourceExhausted
from typing import Optional
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
import re
import uuid
import logging
import threading
from pydantic import Field

from ai.supervisors import get_supervisor
from ai.exceptions import AgentToolError
from ai.llms import gemini_heap, GEMINI_MODEL_PRIORITY

logger = logging.getLogger(__name__)
router = Router(tags=["AI Agents"])

DEFAULT_COOLDOWN_SECONDS = 60

def _parse_retry_delay(error) -> int:
    """Extract retryDelay from Gemini error message, fallback to default."""
    match = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)", str(error))
    if match:
        return int(match.group(1))
    return DEFAULT_COOLDOWN_SECONDS


# ── Supervisor singleton ──────────────────────────────────────────
# Creating the supervisor is expensive (loads LLM, sub-agents, graph).
# We initialize it once on first request and reuse it across all requests.
# PostgresSaver persists conversation state in PostgreSQL.
_supervisor = None
_supervisor_model = None
_supervisor_lock = threading.Lock()


def _get_supervisor(gemini_model_name=None):
    global _supervisor, _supervisor_model
    with _supervisor_lock:
        if _supervisor is None or gemini_model_name != _supervisor_model:
            _supervisor_model = gemini_model_name
            _supervisor = get_supervisor(checkpointer=get_checkpointer(), gemini_model_name=gemini_model_name)
        return _supervisor

def _reset_supervisor():
    global _supervisor, _supervisor_model
    with _supervisor_lock:
        _supervisor = None
        _supervisor_model = None

# ── Schemas ───────────────────────────────────────────────────────
class ChatRequest(Schema):
    message: str = Field(..., max_length=2000)
    thread_id: Optional[str] = None


class ChatResponse(Schema):
    response: str
    thread_id: str


# ── Endpoint ──────────────────────────────────────────────────────
from ninja.throttling import AuthRateThrottle

@router.post("/chat", response=ChatResponse, throttle=AuthRateThrottle('10/m'))
def chat(request, payload: ChatRequest):
    provided_thread_id = payload.thread_id or str(uuid.uuid4())
    user_id = str(request.user.pk)

    internal_thread_id = f"user_{user_id}:{provided_thread_id}"

    config = {
        "configurable": {
            "user_id": user_id,
            "thread_id": internal_thread_id,
        }
    }

    last_error = None
    tried_models = set()
    for attempt in range(len(GEMINI_MODEL_PRIORITY)):
        model_name = gemini_heap.get_best_model()
        if model_name is None or model_name in tried_models:
            raise HttpError(429, "All AI models are rate limited. Try again in a minute.")
        tried_models.add(model_name)
        
        try:
            result = _get_supervisor(gemini_model_name=model_name).invoke(
                {"messages": [HumanMessage(content=payload.message)]},
                config=config,
            )
            break
        except ChatGoogleGenerativeAIError as e:
            cause = e.__cause__ or e.__context__
            if isinstance(cause, ResourceExhausted) or "429" in str(e):
                logger.warning(f"Model {model_name} rate limited (attempt {attempt + 1})")
                gemini_heap.mark_exhausted(model_name, cooldown_seconds=_parse_retry_delay(e))
                _reset_supervisor()
                last_error = e
                continue
            logger.error(f"Gemini model error: {e}")
            raise HttpError(500, "The AI agent encountered a model error.")
        except AgentToolError as e:
            logger.log(e.log_level, f"{type(e).__name__}: {e}")
            raise HttpError(e.status_code, str(e))
        except Exception as e:
            err_str = str(e).lower()
            retryable = ("rate_limit" in err_str or "resource_exhausted" in err_str
                         or "unavailable" in err_str or "deadline_exceeded" in err_str
                         or any(code in str(e) for code in ("429", "503", "500", "504")))
            if retryable:
                logger.warning(f"Model {model_name} unavailable (attempt {attempt + 1}): {e}")
                gemini_heap.mark_exhausted(model_name, cooldown_seconds=_parse_retry_delay(e))
                _reset_supervisor()
                last_error = e
                continue
            logger.error(f"AI agent internal error: {e}", exc_info=True)
            raise HttpError(500, "The AI agent encountered an internal error.")
    else:
        logger.error(f"All Gemini models exhausted. Last error: {last_error}")
        raise HttpError(429, "All AI models are rate limited. Try again in a minute.")


    last_msg = result["messages"][-1]
    ai_response = last_msg.content

    # Handle multi-part content
    if isinstance(ai_response, list):
        ai_response = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in ai_response
        )

    return ChatResponse(response=ai_response, thread_id=provided_thread_id)