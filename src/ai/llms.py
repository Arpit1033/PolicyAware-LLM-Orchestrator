import logging
import heapq
import threading
from datetime import datetime, timedelta
from enum import Enum
from django.conf import settings

logger = logging.getLogger(__name__)

class LLMProvider(str, Enum):
    GEMINI = "gemini"
    GROQ = "groq"

# ── Gemini model priority (lower = better) ───────────────────
GEMINI_MODEL_PRIORITY = {
    "gemini-2.5-flash": 0,
    "gemini-2.0-flash": 1,
    "gemini-3-flash-preview": 2,
    "gemini-2.5-pro": 3,
    "gemini-3.1-pro-preview": 4,
    "gemini-2.5-flash-lite": 5,
    "gemini-2.0-flash-lite": 6,
    "gemini-3.1-flash-lite-preview": 7
}

# ── Heap entry ────────────────────────────────────────────────
class ModelEntry:
    """Heap entry with cooldown-aware comparison."""
    def __init__(self, model_name):
        self.model_name = model_name
        self.cooldown_until = datetime.min
        self.priority = GEMINI_MODEL_PRIORITY[model_name]
    def is_available(self):
        return datetime.now() >= self.cooldown_until
    def _cooldown_bucket(self):
        if self.is_available():
            return datetime.min
        return self.cooldown_until.replace(second=0, microsecond=0)
    def __lt__(self, other):
        my_bucket = self._cooldown_bucket()
        other_bucket = other._cooldown_bucket()
        if my_bucket == other_bucket:
            return self.priority < other.priority
        return my_bucket < other_bucket
    def __repr__(self):
        status = "available" if self.is_available() else f"cooldown until {self.cooldown_until:%H:%M:%S}"
        return f"ModelEntry({self.model_name}, {status})"

# ── Thread-safe Gemini model heap ─────────────────────────────
class GeminiModelHeap:
    """Min-heap of Gemini models sorted by (cooldown_bucket, priority)."""
    def __init__(self):
        self._heap = [ModelEntry(name) for name in GEMINI_MODEL_PRIORITY]
        heapq.heapify(self._heap)
        self._lock = threading.Lock()
    def get_best_model(self):
        """Return the best available model name, or None if all in cooldown."""
        with self._lock:
            if not self._heap:
                return None
            top = self._heap[0]
            if top.is_available():
                return top.model_name
            return None
    def mark_exhausted(self, model_name, cooldown_seconds=60):
        """Update a model's cooldown and re-heapify."""
        with self._lock:
            for entry in self._heap:
                if entry.model_name == model_name:
                    entry.cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
                    logger.warning(f"Model {model_name} exhausted, cooldown {cooldown_seconds}s")
                    break
            heapq.heapify(self._heap)
        
# Module-level singleton
gemini_heap = GeminiModelHeap()

def get_gemini_model(model_name=None):
    from langchain_google_genai import ChatGoogleGenerativeAI
    if model_name is None:
        model_name = gemini_heap.get_best_model()
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        max_retries=1,
        google_api_key=settings.GOOGLE_API_KEY,
    )

def get_groq_model(model_name="llama-3.3-70b-versatile"):
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=model_name,
        temperature=0,
        max_retries=3,
        api_key=settings.GROQ_API_KEY,
    )

_PROVIDER_FACTORIES = {
    LLMProvider.GEMINI: get_gemini_model,
    LLMProvider.GROQ: get_groq_model,
}

def get_llm_model(provider=LLMProvider.GEMINI, model_name=None):
    """
    Returns a LangChain chat model for the given provider.
    
    Args:
        provider: Which LLM provider to use (gemini, groq)
        model_name: Optional override for the model name
    """
    factory = _PROVIDER_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(f"Unknown LLM provider: {provider}")
    
    if model_name:
        return factory(model_name)
    return factory()