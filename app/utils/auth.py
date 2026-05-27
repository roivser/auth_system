from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User
from app.utils.security import decode_token
from sqlalchemy.orm import selectinload
from app.models.user_role import UserRole
from app.models.role_permission import RolePermission

bearer_scheme = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        if user_id is None or jti is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    blacklisted = await db.scalar(
        select(TokenBlacklist).where(TokenBlacklist.jti == jti)
    )
    if blacklisted:
        raise credentials_exception

    user = await db.scalar(select(User).where(User.id == int(user_id)))
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def get_current_admin(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles).selectinload(UserRole.role)
        )
        .where(User.id == current_user.id)
    )
    user_with_roles = result.scalar_one_or_none()

    is_admin = any(ur.role.name == "admin" for ur in (user_with_roles.roles or []))
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


def require_permission(permission_name: str):
    async def checker(
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
    ) -> User:
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.roles)
                .selectinload(UserRole.role)
                .selectinload(Role.permissions)
                .selectinload(RolePermission.permission)
            )
            .where(User.id == current_user.id)
        )
        user = result.scalar_one_or_none()

        for user_role in user.roles:
            for rp in user_role.role.permissions:
                if rp.permission.name == permission_name:
                    return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission_name}' required",
        )

    return checker
