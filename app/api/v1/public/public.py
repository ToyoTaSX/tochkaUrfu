from fastapi import APIRouter, Depends
from app.api.v1.auth.jwt import get_current_user, create_access_token, get_current_admin
from .schemas import UserAuth
from app.database.models import User, DirectionEnum
from app.crud.user import create_user
from app.crud.instrument import get_all_instruments
from app.crud.order import get_orders
from app.crud.transaction import get_transactions_by_ticker

router = APIRouter()

@router.post('/register')
async def register(user: UserAuth):
    user = await create_user(user.name)
    data = {
            "name": user.name,
            "id": str(user.id),
            "role": user.role.name
        }
    token = create_access_token(data)
    data['api_key'] = token
    return data

@router.get('/instrument')
async def public_test():
    return [{
        "name": i.name,
        "ticker": i.ticker
    } for i in await get_all_instruments()]

@router.get('/orderbook/{ticker}')
async def public_test(ticker: str, limit: int = 10):
    return {
        "bid_levels": await get_orders(ticker, DirectionEnum.BID, limit=limit),
        "ask_levels": await get_orders(ticker, DirectionEnum.ASK, limit=limit)
    }

@router.get('/transactions/{ticker}')
async def public_test(ticker: str, limit: int = 10):
    return await get_transactions_by_ticker(ticker, limit)



@router.get('/public_test')
async def public_test():
    return "Public page"

@router.get('/private_test')
async def public_test(user: User = Depends(get_current_user)):
    return user

@router.get('/admin_test')
async def public_test(user: User = Depends(get_current_admin)):
    return user