from ninja import Router, Schema
from langchain_core.messages import HumanMessage
from ai.checkpointer import get_checkpointer
from ninja.errors import HttpError
from google.api_core.exceptions import ResourceExhausted
from typing import Optional
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
import uuid
from pydantic import Field

from ai.supervisors import get_supervisor

router = Router(tags=["AI Agents"])


# ── Supervisor singleton ──────────────────────────────────────────
# Creating the supervisor is expensive (loads LLM, sub-agents, graph).
# We initialize it once on first request and reuse it across all requests.
# PostgresSaver persists conversation state in PostgreSQL.
_supervisor = None

def _get_supervisor():
    global _supervisor
    if _supervisor is None:
        _supervisor = get_supervisor(checkpointer=get_checkpointer())
    return _supervisor


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

    try:
        result = _get_supervisor().invoke(
            {"messages": [HumanMessage(content=payload.message)]},
            config=config,
        )
    except ChatGoogleGenerativeAIError as e:
        cause = e.__cause__ or e.__context__
        if isinstance(cause, ResourceExhausted) or "429" in str(e):
            raise HttpError(429, "AI service is rate limited. Please wait a moment and try again.")
        raise HttpError(500, "The AI agent encountered a model error. Please try again.")
    except Exception:
        raise HttpError(500, "The AI agent encountered an internal error. Please try again.")

    last_msg = result["messages"][-1]
    ai_response = last_msg.content

    # Handle multi-part content
    if isinstance(ai_response, list):
        ai_response = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in ai_response
        )

    return ChatResponse(response=ai_response, thread_id=provided_thread_id)