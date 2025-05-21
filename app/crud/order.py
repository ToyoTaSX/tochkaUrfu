import asyncio
import os
import uuid
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select, asc, desc

from crud.inventory import get_user_inventory
from crud.transaction import create_transaction
from crud.user import __change_balance
from database.database import async_session_maker
from database.models import Order, DirectionEnum, User, OrderStatusEnum

order_lock = asyncio.Lock()


async def cancel_order(order_id: str, user_id: uuid.UUID) -> Optional[Order]:
    async with order_lock:
        async with async_session_maker() as session:
            q = select(Order).where(Order.id == order_id, Order.user_id == user_id)
            result = await session.execute(q)
            order: Order = result.scalars().first()
            if not order:
                return None
            if order.status in [OrderStatusEnum.PARTIALLY_EXECUTED, OrderStatusEnum.EXECUTED]:
                raise HTTPException(400, 'Order executed/partially_executed')
            if order.price is None:
                raise HTTPException(400, 'Order is market')
            if order.price is not None and order.status in [OrderStatusEnum.PARTIALLY_EXECUTED, OrderStatusEnum.NEW]:
                if order.direction == DirectionEnum.ASK:
                    await __change_balance(session, order.user_id, order.instrument_ticker, order.amount)
                elif order.direction == DirectionEnum.BID:
                    await __change_balance(session, order.user_id, os.getenv('BASE_INSTRUMENT_TICKER'), order.amount * order.price)
            order.status = OrderStatusEnum.CANCELLED
            session.add(order)
            await session.commit()
            await session.refresh(order)
            return order

async def get_order(order_id: str) -> Order:
    async with async_session_maker() as session:
        q = select(Order).where(Order.id == order_id)
        result = await session.execute(q)
        return result.scalars().first()


async def get_orders(ticker: str, direction: DirectionEnum, limit: int = 10) -> List[Order]:
    async with async_session_maker() as session:
        return await __get_orders(session, ticker, direction, limit)


async def __get_orders(session, ticker: str, direction: DirectionEnum, limit: int = 10) -> List[Order]:
    q = (
        select(Order)
        #.join(Order.instrument)
        .filter(
            Order.instrument_ticker == ticker,
            Order.direction == direction.name,
            Order.status.in_([OrderStatusEnum.NEW, OrderStatusEnum.PARTIALLY_EXECUTED])
        )
        .order_by(
            desc(Order.price) if direction == DirectionEnum.BID else asc(Order.price),
            Order.created_at
        )
        .limit(limit)
    )
    result = await session.execute(q)
    res = []
    count = 0
    for order in result.scalars().all():
        if count >= limit:
            break
        count += order.amount
        res.append(order)
    return res


async def create_limit_buy_order(ticker, qty, price, user: User):
    async with order_lock:
        async with async_session_maker() as session:
            orderbook = await __get_orders(session, ticker, DirectionEnum.ASK, qty)
            new_order = Order(
                user_id=user.id,
                instrument_ticker=ticker,
                amount=qty,
                filled=0,
                price=price,
                direction=DirectionEnum.BID,
                status=OrderStatusEnum.NEW
            )
            count_to_buy = qty
            balance_to_buy = user.balance
            buy_orders = []
            for o in orderbook:
                if balance_to_buy <= 0:
                    break
                if count_to_buy == 0:
                    break
                if o.price > price:
                    break
                if balance_to_buy < o.price:
                    break

                count_from_order = min(count_to_buy, o.amount, balance_to_buy // o.price)
                buy_orders.append((o, count_from_order))
                count_to_buy -= count_from_order
                balance_to_buy -= count_from_order * o.price

            total_add_balance = 0
            total_add_ticker = 0
            for order, c in buy_orders:
                await __change_balance(session, order.user_id, os.getenv('BASE_INSTRUMENT_TICKER'), c * order.price)
                total_add_balance += -1 * c * order.price
                total_add_ticker += c
                await create_transaction(order.user_id, user.id, order.instrument_ticker, o.amount, o.price)
                if order.amount > c:
                    order.status = OrderStatusEnum.PARTIALLY_EXECUTED
                else:
                    order.status = OrderStatusEnum.EXECUTED
                order.amount -= c
                order.filled += c
                session.add(order)
            await __change_balance(session, user.id, ticker, total_add_ticker)
            await __change_balance(session, user.id, os.getenv('BASE_INSTRUMENT_TICKER'), total_add_balance)

            if total_add_ticker == qty:
                new_order.status = OrderStatusEnum.EXECUTED
            elif total_add_ticker != 0:
                new_order.status = OrderStatusEnum.PARTIALLY_EXECUTED
            new_order.amount -= abs(total_add_ticker)
            new_order.filled += abs(total_add_ticker)

            try:
                await __change_balance(session, user.id, os.getenv('BASE_INSTRUMENT_TICKER'), -1 * new_order.amount * new_order.price)
            except:
                await session.rollback()
                new_order.status = OrderStatusEnum.CANCELLED
                new_order.amount = qty
                new_order.filled = 0
            session.add(new_order)

            await session.commit()
            await session.refresh(new_order)
            return new_order


async def create_limit_sell_order(ticker, qty, price, user: User):
    async with order_lock:
        async with async_session_maker() as session:
            orderbook = await __get_orders(session, ticker, DirectionEnum.BID, qty)
            new_order = Order(
                user_id=user.id,
                instrument_ticker=ticker,
                amount=qty,
                filled=0,
                price=price,
                direction=DirectionEnum.ASK,
                status=OrderStatusEnum.NEW
            )
            inventory = (await get_user_inventory(user.id, ticker))[0]
            if inventory.quantity < qty:
                new_order.status = OrderStatusEnum.CANCELLED
                session.add(new_order)
                await session.commit()
                await session.refresh(new_order)
                return new_order

            count_to_sell = qty
            total_add_balance = 0
            total_add_ticker = 0
            for o in orderbook:
                if count_to_sell == 0:
                    break
                if o.price < price:
                    break

                count_from_order = min(count_to_sell, o.amount)
                count_to_sell -= count_from_order
                total_add_ticker -= count_from_order
                total_add_balance += count_from_order * o.price
                await __change_balance(session, o.user_id, ticker, count_from_order)
                await create_transaction(user.id, o.user_id, o.instrument_ticker, count_to_sell, o.price)
                if o.amount > count_from_order:
                    o.status = OrderStatusEnum.PARTIALLY_EXECUTED
                else:
                    o.status = OrderStatusEnum.EXECUTED
                o.amount -= count_from_order
                o.filled += count_from_order
                session.add(o)

            await __change_balance(session, user.id, ticker, total_add_ticker)
            await __change_balance(session, user.id, os.getenv('BASE_INSTRUMENT_TICKER'), total_add_balance)

            if abs(total_add_ticker) == qty:
                new_order.status = OrderStatusEnum.EXECUTED
            elif abs(total_add_ticker) != 0:
                new_order.status = OrderStatusEnum.PARTIALLY_EXECUTED
            new_order.amount -= abs(total_add_ticker)
            new_order.filled += abs(total_add_ticker)
            try:
                await __change_balance(session, user.id, ticker, -1 * new_order.amount)
            except:
                await session.rollback()
                new_order.status = OrderStatusEnum.CANCELLED
                new_order.amount = qty
                new_order.filled = 0

            session.add(new_order)
            await session.commit()
            await session.refresh(new_order)
            return new_order


async def create_market_buy_order(ticker, qty, user: User):
    async with order_lock:
        async with async_session_maker() as session:
            orderbook = await __get_orders(session, ticker, DirectionEnum.ASK, qty)
            new_order = Order(
                user_id=user.id,
                instrument_ticker=ticker,
                amount=qty,
                filled=0,
                price=None,
                direction=DirectionEnum.BID,
                status=OrderStatusEnum.NEW
            )
            if sum(o.amount for o in orderbook) < qty:
                new_order.status = OrderStatusEnum.CANCELLED
                session.add(new_order)
                await session.commit()
                await session.refresh(new_order)
                return new_order

            need_money = 0
            balance = user.balance
            count_to_buy = qty
            buy_orders = []
            for o in orderbook:
                if balance < need_money:
                    new_order.status = OrderStatusEnum.CANCELLED
                    session.add(new_order)
                    await session.commit()
                    await session.refresh(new_order)
                    return new_order

                if count_to_buy == 0:
                    break
                count_from_order = min(o.amount, count_to_buy)
                need_money += count_from_order * o.price
                count_to_buy -= count_from_order
                buy_orders.append((o, count_from_order))

            total_add_balance = 0
            total_add_ticker = 0
            for order, c in buy_orders:
                await __change_balance(session, order.user_id, os.getenv('BASE_INSTRUMENT_TICKER'), c * order.price)
                total_add_balance += -1 * c * order.price
                total_add_ticker += c
                await create_transaction(o.user_id, user.id, o.instrument_ticker, c, o.price)
                if order.amount > c:
                    order.status = OrderStatusEnum.PARTIALLY_EXECUTED
                else:
                    order.status = OrderStatusEnum.EXECUTED
                order.amount -= c
                order.filled += c
                session.add(order)

            await __change_balance(session, user.id, ticker, total_add_ticker)
            await __change_balance(session, user.id, os.getenv('BASE_INSTRUMENT_TICKER'), total_add_balance)

            new_order.status = OrderStatusEnum.EXECUTED
            new_order.amount -= abs(total_add_ticker)
            new_order.filled += abs(total_add_ticker)
            session.add(new_order)
            await session.commit()
            await session.refresh(new_order)
            return new_order


async def create_market_sell_order(ticker, qty, user: User):
    async with order_lock:
        async with async_session_maker() as session:
            orderbook = await __get_orders(session, ticker, DirectionEnum.BID, qty)
            new_order = Order(
                user_id=user.id,
                instrument_ticker=ticker,
                amount=qty,
                filled=0,
                price=None,
                direction=DirectionEnum.ASK,
                status=OrderStatusEnum.NEW
            )
            inventory = (await get_user_inventory(user.id, ticker))[0]
            if sum(o.amount for o in orderbook) < qty or inventory.quantity < qty:
                new_order.status = OrderStatusEnum.CANCELLED
                session.add(new_order)
                await session.commit()
                await session.refresh(new_order)
                return new_order

            count_to_sell = qty
            total_add_balance = 0
            total_add_ticker = 0
            for o in orderbook:
                if count_to_sell == 0:
                    break
                count_from_order = min(count_to_sell, o.amount)
                count_to_sell -= count_from_order

                await __change_balance(session, o.user_id, ticker, count_from_order)
                total_add_balance += count_from_order * o.price
                total_add_ticker += -1 * count_from_order
                await create_transaction(user.id, o.user_id, o.instrument_ticker, count_from_order, o.price)
                if o.amount > count_from_order:
                    o.status = OrderStatusEnum.PARTIALLY_EXECUTED
                else:
                    o.status = OrderStatusEnum.EXECUTED
                o.amount -= count_from_order
                o.filled += count_from_order
                session.add(o)

            await __change_balance(session, user.id, os.getenv('BASE_INSTRUMENT_TICKER'), total_add_balance)
            await __change_balance(session, user.id, ticker, total_add_ticker)
            new_order.status = OrderStatusEnum.EXECUTED
            new_order.amount -= abs(total_add_ticker)
            new_order.filled += abs(total_add_ticker)
            session.add(new_order)
            await session.commit()
            await session.refresh(new_order)
            return new_order


def inverse_direction(direction):
    for dir in DirectionEnum:
        if dir != direction:
            return dir
