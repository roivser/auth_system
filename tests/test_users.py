import pytest
from httpx import AsyncClient

from app.models import User

pytestmark = pytest.mark.asyncio

REGISTER_PAYLOAD = {
    "last_name": "Петров",
    "first_name": "Пётр",
    "email": "petr@example.com",
    "password": "SecurePass1",
    "password_confirm": "SecurePass1",
}


async def test_register_success(client: AsyncClient):
    resp = await client.post("/users/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "petr@example.com"
    assert data["is_active"] is True
    assert "hashed_password" not in data


async def test_register_duplicate_email(client: AsyncClient, test_user: User):
    resp = await client.post("/users/register", json={
        **REGISTER_PAYLOAD,
        "email": "ivan@example.com",
    })
    assert resp.status_code == 409


async def test_register_password_mismatch(client: AsyncClient):
    resp = await client.post("/users/register", json={
        **REGISTER_PAYLOAD,
        "password_confirm": "DifferentPass1",
    })
    assert resp.status_code == 422


async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/users/register", json={
        **REGISTER_PAYLOAD,
        "password": "short",
        "password_confirm": "short",
    })
    assert resp.status_code == 422


async def test_get_me(client: AsyncClient, auth_headers: dict, test_user: User):
    resp = await client.get("/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == test_user.email
    assert data["first_name"] == test_user.first_name


async def test_get_me_unauthorized(client: AsyncClient):
    resp = await client.get("/users/me")
    assert resp.status_code == 401


async def test_update_me(client: AsyncClient, auth_headers: dict):
    resp = await client.patch("/users/me", headers=auth_headers, json={
        "first_name": "Ваня",
    })
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Ваня"


async def test_update_me_change_password(client: AsyncClient, auth_headers: dict):
    resp = await client.patch("/users/me", headers=auth_headers, json={
        "password": "NewPassword1",
        "password_confirm": "NewPassword1",
    })
    assert resp.status_code == 200

    login = await client.post("/auth/login", json={
        "email": "ivan@example.com",
        "password": "NewPassword1",
    })
    assert login.status_code == 200


async def test_update_me_password_mismatch(client: AsyncClient, auth_headers: dict):
    resp = await client.patch("/users/me", headers=auth_headers, json={
        "password": "NewPassword1",
        "password_confirm": "Mismatch999",
    })
    assert resp.status_code == 422


async def test_delete_me(client: AsyncClient, auth_headers: dict):
    resp = await client.delete("/users/me", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/users/me", headers=auth_headers)
    assert resp.status_code == 401
