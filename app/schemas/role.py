from pydantic import BaseModel


class PermissionOut(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class RoleOut(BaseModel):
    id: int
    name: str
    description: str | None
    permissions: list[PermissionOut] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_permissions(cls, role) -> "RoleOut":
        perms = [
            PermissionOut(
                id=rp.permission.id,
                name=rp.permission.name,
                description=rp.permission.description,
            )
            for rp in role.permissions
        ]
        return cls(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=perms,
        )


class PermissionCreate(BaseModel):
    name: str
    description: str | None = None


class AssignPermissionsRequest(BaseModel):
    permission_ids: list[int]


class AssignRolesRequest(BaseModel):
    role_ids: list[int]
