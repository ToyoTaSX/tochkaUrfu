from fastapi import HTTPException

from crud.instrument import get_instrument_by_ticker
from database.models import Instrument


async def get_instrument_depend(ticker: str) -> Instrument:
    instrument = await get_instrument_by_ticker(ticker)
    if not instrument:
        raise HTTPException(404)
    return instrument