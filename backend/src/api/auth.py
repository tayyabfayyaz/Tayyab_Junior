"""T072: Auth router — login and token refresh endpoints."""

import hashlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.src.config import settings
from backend.src.middleware.auth import create_access_token, verify_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Validate credentials and return JWT access token."""
    # Single-user MVP — compare against owner credentials
    if request.email != settings.owner_email:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password hash (SHA-256 for MVP)
    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    if settings.owner_password_hash and password_hash != settings.owner_password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": request.email, "role": "owner"})
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expiry_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token: str):
    """Issue a new token from an existing valid token."""
    claims = verify_token(token)
    new_token = create_access_token({"sub": claims["sub"], "role": claims.get("role", "owner")})
    return TokenResponse(
        access_token=new_token,
        expires_in=settings.jwt_expiry_minutes * 60,
    )
