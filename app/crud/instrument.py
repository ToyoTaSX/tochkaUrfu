from typing import Optional

from fastapi import HTTPException

from sqlalchemy import select

from database.database import async_session_maker
from database.models import Instrument, User, UserInventory


async def create_instrument(name: str, ticker: str) -> Instrument:
    async with async_session_maker() as session:
        new_instrument = Instrument(name=name, ticker=ticker)
        session.add(new_instrument)

        result = await session.execute(select(User))
        users = result.scalars().all()

        for user in users:
            inv = UserInventory(user=user, instrument=new_instrument, quantity=0.0)
            session.add(inv)

        await session.commit()
        await session.refresh(new_instrument)
        return new_instrument

async def get_instrument_by_ticker(ticker: str) -> Optional[Instrument]:
    async with async_session_maker() as session:
        query = select(Instrument).where(Instrument.ticker == ticker)
        result = await session.execute(query)
        instrument = result.scalars().first()
        return instrument

async def delete_instrument(ticker: str) -> Instrument:
    async with async_session_maker() as session:
        instrument = await get_instrument_by_ticker(ticker)
        if not instrument:
            raise HTTPException(status_code=404, detail='Инструмент с данным ticker е найден')
        await session.delete(instrument)
        await session.commit()
        return instrument

async def get_all_instruments() -> list[Instrument]:
    async with async_session_maker() as session:
        query = select(Instrument)
        result = await session.execute(query)
        instruments = result.scalars().all()
        return instruments