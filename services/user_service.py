from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


class UserService:
    """Сервис для работы с пользователями"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user_by_tg_id(self, tg_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        result = await self.session.execute(
            select(User).where(User.tg_id == tg_id)
        )
        return result.scalars().first()
    
    async def create_user(self, tg_id: int, first_name: str, username: Optional[str] = None, last_name: Optional[str] = None) -> User:
        """Создание нового пользователя"""
        user = User(
            tg_id=tg_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def add_experience(self, user_id: int, xp: int) -> User:
        """Добавление опыта пользователю"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
            
        user.experience += xp
        
        # Проверяем, нужно ли повысить уровень
        # Формула: level_xp = 100 * level^1.5
        next_level_xp = int(100 * (user.level ** 1.5))
        
        if user.experience >= next_level_xp:
            user.level += 1
        
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalars().first()
    
    async def update_completed_tasks_count(self, user_id: int) -> User:
        """Обновление счетчика выполненных задач"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
            
        user.completed_tasks += 1
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_user_stats(self, user_id: int) -> Optional[dict]:
        """Получение статистики пользователя"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
            
        # Формула для следующего уровня
        next_level_xp = int(100 * (user.level ** 1.5))
        
        return {
            "level": user.level,
            "experience": user.experience,
            "next_level_xp": next_level_xp,
            "completed_tasks": user.completed_tasks
        } 

    async def get_all_users(self) -> List[User]:
        """Получение всех пользователей"""
        result = await self.session.execute(select(User))
        return list(result.scalars().all()) 