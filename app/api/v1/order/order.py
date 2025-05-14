from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.auth.jwt import get_current_user
from app.api.v1.order.schemas import CreateOrderScheme
from app.crud.order import create_limit_sell_order, create_limit_buy_order, create_market_buy_order, \
    create_market_sell_order, cancel_order, get_order
from app.crud.user import get_user_orders
from app.database.models import User

router = APIRouter()


@router.get('')
async def order(user: User = Depends(get_current_user)):
    return await get_user_orders(str(user.id))

@router.delete('/{order_id}')
async def order(order_id: str, user: User = Depends(get_current_user)):
    await cancel_order(order_id, user.id)
    return {
        "success": True
    }

@router.get('/{order_id}')
async def order(order_id: str, user: User = Depends(get_current_user)):
    order = await get_order(order_id)
    if order.user_id != user.id:
        raise HTTPException(403)
    return order

@router.post('')
async def order(order: CreateOrderScheme, user: User = Depends(get_current_user)):
    order_ = None
    if order.direction == 'BUY':
        order_ = await buy_order(order, user)
    elif order.direction == 'SELL':
        order_ = await sell_order(order, user)
    return {
        "success": True,
        "order_id": str(order_.id)
    }


async def buy_order(order: CreateOrderScheme, user: User):
    if order.price:
        return await create_limit_buy_order(order.ticker, order.qty, order.price, user)
    return await create_market_buy_order(order.ticker, order.qty, user)


async def sell_order(order: CreateOrderScheme, user: User):
    if order.price:
        return await create_limit_sell_order(order.ticker, order.qty, order.price, user)
    return await create_market_sell_order(order.ticker, order.qty, user)
