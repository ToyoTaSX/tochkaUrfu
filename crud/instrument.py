from sqlalchemy import select

from database.database import async_session_maker
from database.models import Instrument


async def create_instrument(title: str, ticker: str) -> Instrument:
    async with async_session_maker() as session:
        new_instrument = Instrument(title=title, ticker=ticker)
        session.add(new_instrument)
        await session.commit()
        await session.refresh(new_instrument)
        return new_instrument

async def get_instrument_by_id(instrument_id: int) -> Instrument:
    async with async_session_maker() as session:
        result = await session.get(Instrument, instrument_id)
        return result

async def get_instrument_by_ticker(ticker: str) -> Instrument:
    async with async_session_maker() as session:
        query = select(Instrument).where(Instrument.ticker == ticker)
        result = await session.execute(query)
        instrument = result.scalars().first()
        return instrument

async def get_all_instruments() -> list[Instrument]:
    async with async_session_maker() as session:
        query = select(Instrument)
        result = await session.execute(query)
        instruments = result.scalars().all()
        return instruments