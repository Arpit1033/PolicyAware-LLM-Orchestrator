import logging

from ninja_extra import api_controller, http_post, ControllerBase
from ninja.errors import HttpError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from asgiref.sync import async_to_sync

from mypermit import permit_client
from accounts.schemas import RegisterRequestSchema, RegisterResponseSchema
from ai.constants import PERMIT_DEFAULT_ROLE, PERMIT_DEFAULT_TENANT

User = get_user_model()
logger = logging.getLogger(__name__)

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
            async_to_sync(permit_client.api.users.assign_role)({"user": str(user.id), "role": PERMIT_DEFAULT_ROLE, "tenant": PERMIT_DEFAULT_TENANT})
        except Exception as e:
            logger.error(f"Permit.io sync failed for user {user.id}: {e}")

        return 201, RegisterResponseSchema(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        )