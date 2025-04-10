from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from config import DatabaseConfig


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_config: DatabaseConfig):
        self.engine = create_async_engine(
            db_config.get_url(),
            echo=False,
            poolclass=NullPool
        )
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def get_session(self) -> AsyncSession:
        """Получение сессии для работы с БД"""
        async with self.session_factory() as session:
            yield session 