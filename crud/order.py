from typing import Optional, List

from sqlalchemy import select

from database.database import async_session_maker
from database.models import Instrument, Order, DirectionEnum

async def get_orders(ticker: str, direction: DirectionEnum, limit: int = 10) -> List[Order]:
    async with async_session_maker() as session:
        q = (
            select(Order)
            .join(Order.instrument)
            .filter(
                Instrument.ticker == ticker,
                Order.direction == direction.name
            )
            .order_by(Order.amount, Order.created_at)
            .limit(limit)
        )
        result = await session.execute(q)
        return result.scalars().all()