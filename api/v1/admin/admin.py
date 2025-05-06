from fastapi import APIRouter, Depends

from api.v1.auth.jwt import get_current_admin
from database.models import User

router = APIRouter()

@router.post('/instrument')
async def public_test(user: User = Depends(get_current_admin)):
    return user