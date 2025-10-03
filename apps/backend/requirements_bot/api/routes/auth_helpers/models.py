"""Pydantic models for authentication routes."""

from pydantic import BaseModel, field_validator


class RefreshTokenRequest(BaseModel):
    refresh_token: str

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, v):
        if not v or not v.strip():
            raise ValueError("Refresh token cannot be empty")
        if len(v) < 10:
            raise ValueError("Refresh token appears to be invalid")
        return v.strip()


class LogoutRequest(BaseModel):
    refresh_token: str | None = None

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError("Refresh token cannot be empty if provided")
            if len(v) < 10:
                raise ValueError("Refresh token appears to be invalid")
            return v.strip()
        return v
