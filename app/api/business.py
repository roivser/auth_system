"""
Mock business views demonstrating the access control system.
No real DB tables — returns fictional data or raises 401/403.
"""
from fastapi import APIRouter, Depends

from app.utils.auth import get_current_user, require_permission
from app.models.user import User

router = APIRouter(prefix="/business", tags=["business (mock)"])


@router.get("/products")
async def list_products(
    _: User = Depends(require_permission("products:read")),
):
    return [
        {"id": 1, "name": "Widget A", "price": 9.99, "stock": 100},
        {"id": 2, "name": "Gadget B", "price": 24.99, "stock": 45},
        {"id": 3, "name": "Doohickey C", "price": 4.49, "stock": 200},
    ]


@router.post("/products")
async def create_product(
    _: User = Depends(require_permission("products:write")),
):
    return {"id": 4, "name": "New Product", "price": 0.0, "stock": 0}


@router.get("/orders")
async def list_orders(
    _: User = Depends(require_permission("orders:read")),
):
    return [
        {"id": 101, "status": "shipped", "total": 34.98},
        {"id": 102, "status": "pending", "total": 9.99},
    ]


@router.get("/orders/{order_id}")
async def get_order(
    order_id: int,
    _: User = Depends(require_permission("orders:read")),
):
    return {"id": order_id, "status": "shipped", "total": 34.98, "items": ["Widget A x2"]}


@router.get("/reports")
async def get_reports(
    _: User = Depends(require_permission("reports:read")),
):
    return {
        "revenue_this_month": 15420.50,
        "orders_count": 312,
        "active_users": 87,
    }


@router.get("/profile", summary="Authenticated endpoint (any logged-in user)")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello, {current_user.first_name}!", "user_id": current_user.id}