import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.utils.security import create_refresh_token

pytestmark = pytest.mark.asyncio


async def test_login_success(client: AsyncClient, test_user: User):
    resp = await client.post("/auth/login", json={
        "email": "ivan@example.com",
        "password": "Password123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(client: AsyncClient, test_user: User):
    resp = await client.post("/auth/login", json={
        "email": "ivan@example.com",
        "password": "WrongPass999",
    })
    assert resp.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "Password123",
    })
    assert resp.status_code == 401


async def test_login_deactivated_account(client: AsyncClient, db: AsyncSession, test_user: User):
    test_user.is_active = False
    await db.commit()

    resp = await client.post("/auth/login", json={
        "email": "ivan@example.com",
        "password": "Password123",
    })
    assert resp.status_code == 401
    assert "deactivated" in resp.json()["detail"].lower()


async def test_logout_success(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/auth/logout", headers=auth_headers)
    assert resp.status_code == 204


async def test_logout_token_blacklisted(client: AsyncClient, auth_headers: dict):
    await client.post("/auth/logout", headers=auth_headers)
    resp = await client.get("/users/me", headers=auth_headers)
    assert resp.status_code == 401


async def test_refresh_success(client: AsyncClient, test_user: User):
    login = await client.post("/auth/login", json={
        "email": "ivan@example.com",
        "password": "Password123",
    })
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_refresh_with_access_token_rejected(client: AsyncClient, test_user: User):
    login = await client.post("/auth/login", json={
        "email": "ivan@example.com",
        "password": "Password123",
    })
    access_token = login.json()["access_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post("/auth/refresh", json={"refresh_token": "not.a.token"})
    assert resp.status_code == 401
