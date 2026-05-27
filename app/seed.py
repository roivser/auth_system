"""Наполнение БД"""
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.models import Permission, Role, RolePermission, User, UserRole
from app.core.database import Base
from app.utils.security import hash_password

PERMISSIONS = [
    ("products:read", "View product list"),
    ("products:write", "Create/update products"),
    ("orders:read", "View orders"),
    ("orders:write", "Create/update orders"),
    ("reports:read", "View analytics reports"),
]

ROLES = {
    "admin": {
        "description": "Full system access",
        "permissions": [
            "products:read", "products:write",
            "orders:read", "orders:write",
            "reports:read",
        ],
    },
    "manager": {
        "description": "Can manage orders and view reports",
        "permissions": ["orders:read", "orders:write", "reports:read", "products:read"],
    },
    "viewer": {
        "description": "Read-only access to products and orders",
        "permissions": ["products:read", "orders:read"],
    },
}

USERS = [
    {
        "last_name": "Иванов",
        "first_name": "Иван",
        "patronymic": "Иванович",
        "email": "admin@example.com",
        "password": "Admin1234!",
        "role": "admin",
    },
    {
        "last_name": "Петрова",
        "first_name": "Анна",
        "patronymic": "Сергеевна",
        "email": "manager@example.com",
        "password": "Manager1234!",
        "role": "manager",
    },
    {
        "last_name": "Сидоров",
        "first_name": "Пётр",
        "patronymic": None,
        "email": "viewer@example.com",
        "password": "Viewer1234!",
        "role": "viewer",
    },
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        perm_map: dict[str, Permission] = {}
        for name, desc in PERMISSIONS:
            perm = await db.scalar(select(Permission).where(Permission.name == name))
            if not perm:
                perm = Permission(name=name, description=desc)
                db.add(perm)
                await db.flush()
            perm_map[name] = perm

        role_map: dict[str, Role] = {}
        for role_name, cfg in ROLES.items():
            role = await db.scalar(select(Role).where(Role.name == role_name))
            if not role:
                role = Role(name=role_name, description=cfg["description"])
                db.add(role)
                await db.flush()
            role_map[role_name] = role

            for perm_name in cfg["permissions"]:
                perm = perm_map[perm_name]
                existing = await db.scalar(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id,
                    )
                )
                if not existing:
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))

        for u_data in USERS:
            user = await db.scalar(select(User).where(User.email == u_data["email"]))
            if not user:
                user = User(
                    last_name=u_data["last_name"],
                    first_name=u_data["first_name"],
                    patronymic=u_data["patronymic"],
                    email=u_data["email"],
                    hashed_password=hash_password(u_data["password"]),
                )
                db.add(user)
                await db.flush()

            role = role_map[u_data["role"]]
            existing_ur = await db.scalar(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == role.id,
                )
            )
            if not existing_ur:
                db.add(UserRole(user_id=user.id, role_id=role.id))

        await db.commit()
        print("Seed completed successfully.")
        print("\nTest accounts:")
        for u in USERS:
            print(f"  {u['role']:10s}  {u['email']}  /  {u['password']}")


if __name__ == "__main__":
    asyncio.run(seed())