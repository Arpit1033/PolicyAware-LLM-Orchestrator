from ninja import Schema
from ninja_extra import NinjaExtraAPI
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController
from documents.api import router as documents_router
from ai.api import router as ai_router


class HealthResponse(Schema):
    status: str
    version: str


api = NinjaExtraAPI(
    title="PolicyAware LLM Orchestrator API",
    version="1.0.0",
    description="Multi-agent AI orchestration with Permit.io RBAC",
    auth=JWTAuth(),
)

api.register_controllers(NinjaJWTDefaultController)
api.add_router("/documents/", documents_router)
api.add_router("/ai/", ai_router)

@api.get("/health", tags=["System"], auth=None, response=HealthResponse)
def health(request):
    return HealthResponse(status="ok", version="1.0.0")

