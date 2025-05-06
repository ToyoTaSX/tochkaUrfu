from typing import List

from sqlalchemy import select

from database.database import async_session_maker
from database.models import Transaction, Instrument


async def get_transactions_by_ticker(ticker: str, limit: int = 10) -> List[Transaction]:
    async with async_session_maker() as session:
        stmt = (
            select(Transaction)
            .join(Transaction.instrument)
            .filter(Instrument.ticker == ticker)
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
        )

        result = await session.execute(stmt)
        transactions = result.scalars().all()

        return transactions