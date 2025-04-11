from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import Database


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для внедрения сессии базы данных в хендлеры"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Внедряем сессию БД
        async for session in self.db.get_session():
            data["session"] = session
            # Передаем управление следующему обработчику
            return await handler(event, data)


def register_all_middlewares(dp: Dispatcher, db: Database):
    """Регистрирует все middleware"""
    dp.update.middleware(DatabaseMiddleware(db)) 