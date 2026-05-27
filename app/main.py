from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import engine
from app.core.database import Base
from app.api import admin, auth, business, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # Вместо Alembic
    yield


app = FastAPI(
    title="Auth & RBAC API",
    description="Custom authentication and RBAC system",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(business.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
