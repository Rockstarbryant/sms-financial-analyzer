"""Pydantic schemas for authentication and cloud sync."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class RawSmsIn(BaseModel):
    """A single SMS message sent by the Android companion app."""

    sender: str = Field(min_length=1, max_length=64)
    body: str = Field(min_length=1, max_length=2000)
    timestamp: datetime


class CloudSyncRequest(BaseModel):
    """Batch of SMS messages from the Android companion app."""

    messages: list[RawSmsIn] = Field(min_length=1, max_length=10000)
