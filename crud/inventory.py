from typing import List

from sqlalchemy import select
from database.database import async_session_maker
from database.models import UserInventory

async def get_user_inventory(user_id: int) -> List[UserInventory]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserInventory).where(UserInventory.user_id == user_id)
        )

        return result.scalars().all()