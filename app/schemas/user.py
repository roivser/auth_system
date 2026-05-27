from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator, model_validator


class UserCreate(BaseModel):
    last_name: str
    first_name: str
    patronymic: str | None = None
    email: EmailStr
    password: str
    password_confirm: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "UserCreate":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class UserUpdate(BaseModel):
    last_name: str | None = None
    first_name: str | None = None
    patronymic: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    password_confirm: str | None = None

    @model_validator(mode="after")
    def passwords_match(self) -> "UserUpdate":
        if self.password or self.password_confirm:
            if self.password != self.password_confirm:
                raise ValueError("Passwords do not match")
        return self


class UserRoleOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: int
    last_name: str
    first_name: str
    patronymic: str | None
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    roles: list[UserRoleOut] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_roles(cls, user) -> "UserOut":
        role_names = [UserRoleOut(id=ur.role.id, name=ur.role.name) for ur in user.roles]
        return cls(
            id=user.id,
            last_name=user.last_name,
            first_name=user.first_name,
            patronymic=user.patronymic,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=role_names,
        )
