from ninja import Schema
from pydantic import EmailStr, Field, SecretStr
from typing import Optional

class RegisterRequestSchema(Schema):
    username: str = Field(..., min_length=3, max_length=30, description="Username must be between 3 and 30 characters long")
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=30)
    last_name: Optional[str] = Field(None, max_length=30)
    password: SecretStr = Field(..., min_length=8, max_length=128, description="Password must be between 8 and 128 characters long")

class RegisterResponseSchema(Schema):
    id: int
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    message: str = "User registered successfully"