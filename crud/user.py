
from typing import Optional

from sqlalchemy import select

from database.models import User, RoleEnum
from database.database import async_session_maker
from passlib.context import CryptContext


async def create_user(name: str, role: RoleEnum=RoleEnum.USER) -> User:
    async with async_session_maker() as session:
        new_user = User(name=name, role=role)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user


async def get_user(name: str) -> Optional[User]:
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.name == name))
        user = result.scalars().first()
        return user
