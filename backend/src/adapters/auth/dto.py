from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, SecretStr


class RegisterRequestDTO(BaseModel):
    email: str
    password: SecretStr


class RegisterResponseDTO(BaseModel):
    user_id: UUID


class SignInRequestDTO(BaseModel):
    email: str
    password: SecretStr


class SignInResponseDTO(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
