from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.utils.auth import get_current_admin
from app.models import Permission, Role, RolePermission, User, UserRole
from app.schemas.role import (
    AssignPermissionsRequest,
    AssignRolesRequest,
    PermissionCreate,
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleUpdate,
)
from app.schemas.user import UserOut
from app.utils.user import get_user_with_roles

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_admin),
):
    result = await db.execute(select(Permission))
    return result.scalars().all()


@router.post("/permissions", response_model=PermissionOut, status_code=201)
async def create_permission(
        data: PermissionCreate,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_admin),
):
    existing = await db.scalar(select(Permission).where(Permission.name == data.name))
    if existing:
        raise HTTPException(status_code=409, detail="Permission already exists")
    perm = Permission(name=data.name, description=data.description)
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return perm


@router.delete("/permissions/{permission_id}", status_code=204)
async def delete_permission(
        permission_id: int,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_admin),
):
    perm = await db.get(Permission, permission_id)
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    await db.delete(perm)
    await db.commit()


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Role).options(
            selectinload(Role.permissions).selectinload(RolePermission.permission)
        )
    )
    roles = result.scalars().all()
    return [RoleOut.from_orm_with_permissions(r) for r in roles]


@router.post("/roles", response_model=RoleOut, status_code=201)
async def create_role(
        data: RoleCreate,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_admin),
):
    existing = await db.scalar(select(Role).where(Role.name == data.name))
    if existing:
        raise HTTPException(status_code=409, detail="Role already exists")
    role = Role(name=data.name, description=data.description)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return RoleOut(id=role.id, name=role.name, description=role.description, permissions=[])


@router.patch("/roles/{role_id}", response_model=RoleOut)
async def update_role(
        role_id: int,
        data: RoleUpdate,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
        .where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    await db.commit()
    await db.refresh(role)
    return RoleOut.from_orm_with_permissions(role)


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(
        role_id: int,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_admin),
):
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    await db.delete(role)
    await db.commit()


@router.put("/roles/{role_id}/permissions", response_model=RoleOut)
async def set_role_permissions(
        role_id: int,
        data: AssignPermissionsRequest,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
        .where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))

    for perm_id in data.permission_ids:
        perm = await db.get(Permission, perm_id)
        if not perm:
            raise HTTPException(status_code=404, detail=f"Permission {perm_id} not found")
        db.add(RolePermission(role_id=role_id, permission_id=perm_id))

    await db.commit()

    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
        .where(Role.id == role_id)
    )
    role = result.scalar_one()
    return RoleOut.from_orm_with_permissions(role)


@router.get("/users", response_model=list[UserOut])
async def list_users(
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(User).options(
            selectinload(User.roles).selectinload(UserRole.role)
        )
    )
    users = result.scalars().all()
    return [UserOut.from_orm_with_roles(u) for u in users]


@router.put("/users/{user_id}/roles", response_model=UserOut)
async def set_user_roles(
        user_id: int,
        data: AssignRolesRequest,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute(delete(UserRole).where(UserRole.user_id == user_id))

    for role_id in data.role_ids:
        role = await db.get(Role, role_id)
        if not role:
            raise HTTPException(status_code=404, detail=f"Role {role_id} not found")
        db.add(UserRole(user_id=user_id, role_id=role_id))

    await db.commit()
    user_with_roles = await get_user_with_roles(db, user_id)
    return UserOut.from_orm_with_roles(user_with_roles)
