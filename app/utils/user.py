from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.utils.security import hash_password


async def get_user_with_roles(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing:
        return None

    user = User(
        last_name=data.last_name,
        first_name=data.first_name,
        patronymic=data.patronymic,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.patronymic is not None:
        user.patronymic = data.patronymic
    if data.email is not None:
        taken = await db.scalar(
            select(User).where(User.email == data.email, User.id != user.id)
        )
        if taken:
            return None
        user.email = data.email
    if data.password:
        user.hashed_password = hash_password(data.password)

    await db.commit()
    await db.refresh(user)
    return user


async def soft_delete_user(db: AsyncSession, user: User) -> None:
    user.is_active = False
    await db.commit()
