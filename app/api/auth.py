from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.utils.auth import get_current_user
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    token_expires_at,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    token = credentials.credentials
    payload = decode_token(token)
    jti = payload["jti"]
    expires = token_expires_at(token)

    existing = await db.scalar(
        select(TokenBlacklist).where(TokenBlacklist.jti == jti)
    )
    if not existing:
        db.add(TokenBlacklist(jti=jti, expires_at=expires))
        await db.commit()


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id = int(payload["sub"])
        jti = payload["jti"]
    except (JWTError, ValueError):
        raise credentials_exception

    blacklisted = await db.scalar(
        select(TokenBlacklist).where(TokenBlacklist.jti == jti)
    )
    if blacklisted:
        raise credentials_exception

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise credentials_exception

    return AccessTokenResponse(access_token=create_access_token(user.id))
