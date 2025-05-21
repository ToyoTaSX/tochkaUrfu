import uuid
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException

from api.v1.auth.jwt import get_current_user
from api.v1.order.schemas import CreateOrderScheme
from crud.instrument import get_instrument_by_ticker
from crud.order import create_limit_sell_order, create_limit_buy_order, create_market_buy_order, \
    create_market_sell_order, cancel_order, get_order
from crud.user import get_user_orders
from database.models import User, OrderStatusEnum, DirectionEnum

router = APIRouter()


@router.get('')
async def order(user: User = Depends(get_current_user)):
    return await get_user_orders(str(user.id))


@router.delete('/{order_id}')
async def order(order_id: str, user: User = Depends(get_current_user)):
    canceled = await cancel_order(order_id, user.id)
    if not canceled:
        raise HTTPException(404, detail='order not found')
    return {
        "success": True
    }


@router.get('/{order_id}')
async def order(order_id: str, user: User = Depends(get_current_user)):
    try:
        uu = uuid.UUID(order_id)
    except Exception as e:
        print(e)
        raise HTTPException(404)

    order = await get_order(order_id)
    if order is None:
        raise HTTPException(404)
    if order.user_id != user.id:
        raise HTTPException(403)
    your_datetime = order.created_at

    # Убедись, что datetime в UTC:
    datetime_utc = your_datetime.astimezone(timezone.utc)

    # Получаем строку нужного формата:
    formatted_timestamp = datetime_utc.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    return {
        "id": order.id,
        "status": order.status.value,
        "user_id": order.user_id,
        "timestamp": formatted_timestamp,
        "body": {
            "direction": "BUY" if order.direction == DirectionEnum.BID else 'SELL',
            "ticker": order.instrument_ticker,
            "qty": order.amount + order.filled,
            "price": order.price
        },
        "filled": order.filled
    }


@router.post('')
async def order(order: CreateOrderScheme, user: User = Depends(get_current_user)):
    order_ = None
    instrument = await get_instrument_by_ticker(order.ticker)
    if not instrument:
        raise HTTPException(404, detail='ticker unexist')
    if order.direction == 'BUY':
        order_ = await buy_order(order, user)
    elif order.direction == 'SELL':
        order_ = await sell_order(order, user)
    if order_.status == OrderStatusEnum.CANCELLED:
        raise HTTPException(422, detail='ORDER CANCELLED')
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
