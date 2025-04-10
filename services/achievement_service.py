from typing import List, Optional, Dict

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Achievement, UserAchievement, User, Task, TaskStatus
from services.user_service import UserService


class AchievementService:
    """Сервис для работы с достижениями"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_service = UserService(session)
    
    async def get_all_achievements(self) -> List[Achievement]:
        """Получение всех достижений"""
        result = await self.session.execute(select(Achievement))
        return list(result.scalars().all())
    
    async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """Получение всех достижений пользователя"""
        result = await self.session.execute(
            select(UserAchievement).where(UserAchievement.user_id == user_id)
        )
        return list(result.scalars().all())
    
    async def unlock_achievement(self, user_id: int, achievement_id: int) -> Optional[UserAchievement]:
        """Разблокировка достижения для пользователя"""
        # Проверка, есть ли уже такое достижение у пользователя
        existing = await self.session.execute(
            select(UserAchievement).where(
                and_(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement_id
                )
            )
        )
        
        if existing.scalars().first():
            return None  # Достижение уже разблокировано
        
        # Проверяем, существует ли достижение
        achievement = await self.session.execute(
            select(Achievement).where(Achievement.id == achievement_id)
        )
        achievement = achievement.scalars().first()
        
        if not achievement:
            return None  # Достижение не найдено
        
        # Создаем запись о разблокировке
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id
        )
        
        self.session.add(user_achievement)
        
        # Даем пользователю опыт за достижение
        await self.user_service.add_experience(user_id, achievement.xp_reward)
        
        await self.session.commit()
        await self.session.refresh(user_achievement)
        
        return user_achievement
    
    async def check_achievements(self, user_id: int) -> List[Achievement]:
        """Проверка достижений для пользователя и их разблокировка при выполнении условий"""
        # Получаем все достижения
        all_achievements = await self.get_all_achievements()
        
        # Получаем уже разблокированные достижения
        unlocked_ids = []
        unlocked = await self.get_user_achievements(user_id)
        
        for ua in unlocked:
            unlocked_ids.append(ua.achievement_id)
        
        # Достижения, которые можно разблокировать
        newly_unlocked = []
        
        # Проверяем каждое достижение
        for achievement in all_achievements:
            # Пропускаем уже разблокированные
            if achievement.id in unlocked_ids:
                continue
            
            # Проверяем условие достижения
            condition_met = await self._check_achievement_condition(user_id, achievement)
            
            if condition_met:
                # Разблокируем достижение
                await self.unlock_achievement(user_id, achievement.id)
                newly_unlocked.append(achievement)
                
        return newly_unlocked
    
    async def _check_achievement_condition(self, user_id: int, achievement: Achievement) -> bool:
        """Проверка выполнения условия для достижения"""
        condition_type = achievement.condition_type
        condition_value = achievement.condition_value
        
        if condition_type == "tasks_count":
            # Количество выполненных задач
            result = await self.session.execute(
                select(func.count(Task.id)).where(
                    and_(
                        Task.user_id == user_id,
                        Task.status == TaskStatus.DONE
                    )
                )
            )
            count = result.scalar_one()
            return count >= condition_value
            
        elif condition_type == "level":
            # Достижение определенного уровня
            user = await self.user_service.get_user_by_id(user_id)
            return user and user.level >= condition_value
            
        elif condition_type == "important_tasks":
            # Количество выполненных важных задач
            result = await self.session.execute(
                select(func.count(Task.id)).where(
                    and_(
                        Task.user_id == user_id,
                        Task.status == TaskStatus.DONE,
                        Task.is_important == True
                    )
                )
            )
            count = result.scalar_one()
            return count >= condition_value
            
        # Другие типы условий можно добавить по мере необходимости
        
        return False
    
    async def create_default_achievements(self) -> List[Achievement]:
        """Создание стандартных достижений в системе"""
        default_achievements = [
            {
                "name": "Первые шаги",
                "description": "Выполнить первую задачу",
                "condition_type": "tasks_count",
                "condition_value": 1,
                "xp_reward": 50
            },
            {
                "name": "Продуктивность растет",
                "description": "Выполнить 10 задач",
                "condition_type": "tasks_count",
                "condition_value": 10,
                "xp_reward": 100
            },
            {
                "name": "Мастер дел",
                "description": "Выполнить 50 задач",
                "condition_type": "tasks_count",
                "condition_value": 50,
                "xp_reward": 200
            },
            {
                "name": "Уровень 5",
                "description": "Достичь 5 уровня",
                "condition_type": "level",
                "condition_value": 5,
                "xp_reward": 300
            },
            {
                "name": "Приоритеты на месте",
                "description": "Выполнить 5 важных задач",
                "condition_type": "important_tasks",
                "condition_value": 5,
                "xp_reward": 150
            }
        ]
        
        created_achievements = []
        
        for ach_data in default_achievements:
            # Проверяем, существует ли уже такое достижение
            result = await self.session.execute(
                select(Achievement).where(Achievement.name == ach_data["name"])
            )
            existing = result.scalars().first()
            
            if not existing:
                achievement = Achievement(**ach_data)
                self.session.add(achievement)
                created_achievements.append(achievement)
        
        if created_achievements:
            await self.session.commit()
            
            # Обновляем созданные объекты после коммита
            for achievement in created_achievements:
                await self.session.refresh(achievement)
        
        return created_achievements 