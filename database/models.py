import asyncio
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database.database import Base, engine
from datetime import datetime
from enum import Enum as PythonEnum

class RoleEnum(PythonEnum):
    USER = "user"
    ADMIN = "admin"

class DirectionEnum(PythonEnum):
    ASK = "ask"
    BID = "bid"

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.USER)
    balance = Column(Float, default=0.0)

    # Создаем отношения
    orders = relationship("Order", back_populates="user")
    transactions_sent = relationship("Transaction", foreign_keys='Transaction.user_from_id', back_populates="user_from")
    transactions_received = relationship("Transaction", foreign_keys='Transaction.user_to_id', back_populates="user_to")
    inventory = relationship("UserInventory", back_populates="user")

class UserInventory(Base):
    __tablename__ = 'user_inventories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    instrument_id = Column(Integer, ForeignKey('instruments.id'), nullable=False)
    quantity = Column(Float, nullable=False, default=0.0)

    # Создаем отношения
    user = relationship("User", back_populates="inventory")
    instrument = relationship("Instrument")


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    instrument_id = Column(Integer, ForeignKey('instruments.id'))
    amount = Column(Float, nullable=False)
    direction = Column(Enum(DirectionEnum), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Создаем отношения
    user = relationship("User", back_populates="orders")
    instrument = relationship("Instrument")


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_from_id = Column(Integer, ForeignKey('users.id'))
    user_to_id = Column(Integer, ForeignKey('users.id'))
    instrument_id = Column(Integer, ForeignKey('instruments.id'))
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Создаем отношения
    user_from = relationship("User", foreign_keys=[user_from_id], back_populates="transactions_sent")
    user_to = relationship("User", foreign_keys=[user_to_id], back_populates="transactions_received")
    instrument = relationship("Instrument")


class Instrument(Base):
    __tablename__ = 'instruments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    ticker = Column(String(10), unique=True, nullable=False)
