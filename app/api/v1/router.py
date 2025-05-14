import os

from fastapi import APIRouter, Depends

from app.database.models import User
from .public.public import router as public_router
from .admin.admin import router as admin_router
from .order.order import router as order_router
from app.api.v1.auth.jwt import get_current_user
from app.crud.inventory import get_user_inventory

router = APIRouter()
router.include_router(public_router, prefix='/public')
router.include_router(admin_router, prefix='/admin')
router.include_router(order_router, prefix='/order')

@router.get("/balance")
async def balance(user: User = Depends(get_current_user)):
    inv = await get_user_inventory(user.id)
    result = {i.instrument_ticker: i.quantity for i in inv}
    result[os.getenv('BASE_INSTRUMENT_TICKER')] = user.balance
    return result
