from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# --- User Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    role: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Project Schemas ---
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[str] = None
