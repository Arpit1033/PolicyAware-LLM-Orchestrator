import logging

from ninja_extra import api_controller, http_post, ControllerBase, http_patch
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from asgiref.sync import async_to_sync

from mypermit import permit_client
from accounts.schemas import RegisterRequestSchema, RegisterResponseSchema, AgentRoleUpdateSchema, AgentRoleResponseSchema
from ai.constants import (
    PERMIT_DEFAULT_ROLE, PERMIT_DEFAULT_TENANT, PERMIT_USER_ASSIGNABLE_ROLES,
    PERMIT_RESOURCE_INSTANCE, is_resource_role
)

User = get_user_model()
logger = logging.getLogger(__name__)


def _assign_permit_role(user_id: str, role: str):
    """Assign a role using the correct Permit.io API based on role type."""
    if is_resource_role(role):
        async_to_sync(permit_client.api.role_assignments.assign)({
            "user": user_id, "role": role,
            "tenant": PERMIT_DEFAULT_TENANT,
            "resource_instance": PERMIT_RESOURCE_INSTANCE,
        })
    else:
        async_to_sync(permit_client.api.users.assign_role)({
            "user": user_id, "role": role, "tenant": PERMIT_DEFAULT_TENANT,
        })


def _unassign_permit_role(user_id: str, role: str):
    """Unassign a role using the correct Permit.io API based on role type."""
    if is_resource_role(role):
        async_to_sync(permit_client.api.role_assignments.unassign)({
            "user": user_id, "role": role,
            "tenant": PERMIT_DEFAULT_TENANT,
            "resource_instance": PERMIT_RESOURCE_INSTANCE,
        })
    else:
        async_to_sync(permit_client.api.users.unassign_role)({
            "user": user_id, "role": role, "tenant": PERMIT_DEFAULT_TENANT,
        })


@api_controller("/auth", tags=["Authentication"], auth=None)
class AuthController(ControllerBase):
    @http_post("/register", url_name="register", response={201: RegisterResponseSchema})
    def register(self, payload: RegisterRequestSchema):
        if User.objects.filter(username=payload.username).exists():
            raise HttpError(409, "Username already taken")
        if User.objects.filter(email=payload.email).exists():
            raise HttpError(409, "Email already taken")

        try:
            validate_password(payload.password.get_secret_value())
        except ValidationError as e:
            raise HttpError(400, e.messages)

        user = User.objects.create_user(
            username=payload.username,
            email=payload.email,
            password=payload.password.get_secret_value(),
            first_name=payload.first_name or "",
            last_name=payload.last_name or "",
        )

        try:
            async_to_sync(permit_client.api.users.sync)({"key": str(user.id), "email": user.email})
            _assign_permit_role(str(user.id), PERMIT_DEFAULT_ROLE)
        except Exception as e:
            logger.error(f"Permit.io sync failed for user {user.id}: {e}")

        return 201, RegisterResponseSchema(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        )

@api_controller("/auth", tags=["AI Agent Permissions"], auth=JWTAuth())
class AgentRoleController(ControllerBase):
    @http_patch("/agent-role", url_name="update_agent_role", response={200: AgentRoleResponseSchema})
    def update_agent_role(self, request, payload: AgentRoleUpdateSchema):
        user_id = str(request.user.pk)

        if payload.role not in PERMIT_USER_ASSIGNABLE_ROLES:
            raise HttpError(400, f"Invalid role. Allowed roles: {', '.join(PERMIT_USER_ASSIGNABLE_ROLES)}")

        try:
            # Ensure user exists in Permit.io
            async_to_sync(permit_client.api.users.sync)(
                {"key": user_id, "email": request.user.email}
            )

            # Unassign all existing roles first
            for role in PERMIT_USER_ASSIGNABLE_ROLES:
                try:
                    _unassign_permit_role(user_id, role)
                except Exception:
                    pass  # Role might not be assigned, that's fine

            # Assign the new role
            _assign_permit_role(user_id, payload.role)
        except Exception as e:
            logger.error(f"Permit.io role update failed for user {user_id}: {e}")
            raise HttpError(502, "Failed to update agent role. Please try again.")

        logger.info(f"User {user_id} updated agent role to '{payload.role}'")
        return AgentRoleResponseSchema(role=payload.role)

