from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Task, User, TaskStatus, TaskPriority, TaskCategory


class TaskService:
    """Сервис для работы с задачами"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_task(self, user_id: int, title: str, description: Optional[str] = None,
                         priority: TaskPriority = TaskPriority.MEDIUM,
                         due_date: Optional[date] = None,
                         category_id: Optional[int] = None) -> Task:
        """Создание новой задачи"""
        task = Task(
            user_id=user_id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            category_id=category_id,
            # Расчет опыта за задачу в зависимости от приоритета
            xp_reward=self._calculate_xp_reward(priority),
            is_important=priority in [TaskPriority.HIGH, TaskPriority.CRITICAL]
        )
        
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task
    
    def _calculate_xp_reward(self, priority: TaskPriority) -> int:
        """Расчет награды опыта за выполнение задачи"""
        if priority == TaskPriority.LOW:
            return 5
        elif priority == TaskPriority.MEDIUM:
            return 10
        elif priority == TaskPriority.HIGH:
            return 20
        elif priority == TaskPriority.CRITICAL:
            return 30
        return 10
    
    async def get_user_tasks(self, user_id: int, status_filter: Optional[List[TaskStatus]] = None, 
                           category_id: Optional[int] = None) -> List[Task]:
        """Получение задач пользователя с фильтрацией по статусу и категории"""
        query = select(Task).where(Task.user_id == user_id)
        
        if status_filter:
            conditions = [Task.status == s for s in status_filter]
            query = query.where(or_(*conditions))
        
        if category_id is not None:
            query = query.where(Task.category_id == category_id)
        
        result = await self.session.execute(query.order_by(Task.due_date, Task.priority.desc()))
        return list(result.scalars().all())
    
    async def get_task_by_id(self, task_id: int, user_id: int) -> Optional[Task]:
        """Получение задачи по ID"""
        result = await self.session.execute(
            select(Task).where(
                and_(
                    Task.id == task_id,
                    Task.user_id == user_id
                )
            )
        )
        return result.scalars().first()
    
    async def update_task(self, task_id: int, user_id: int, update_data: Dict[str, Any]) -> Optional[Task]:
        """Обновление задачи"""
        task = await self.get_task_by_id(task_id, user_id)
        if not task:
            return None
        
        # Обновляем поля задачи
        for field, value in update_data.items():
            if hasattr(task, field):
                setattr(task, field, value)
        
        await self.session.commit()
        await self.session.refresh(task)
        return task
    
    async def delete_task(self, task_id: int, user_id: int) -> bool:
        """Удаление задачи"""
        task = await self.get_task_by_id(task_id, user_id)
        if not task:
            return False
        
        await self.session.delete(task)
        await self.session.commit()
        return True
    
    async def complete_task(self, task_id: int, user_id: int) -> Optional[Task]:
        """Отметка задачи как выполненной"""
        task = await self.get_task_by_id(task_id, user_id)
        if not task:
            return None
        
        task.status = TaskStatus.DONE
        task.completed_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(task)
        return task
    
    async def set_task_in_progress(self, task_id: int, user_id: int) -> Optional[Task]:
        """Установка статуса задачи 'в процессе'"""
        task = await self.get_task_by_id(task_id, user_id)
        if not task:
            return None
        
        task.status = TaskStatus.IN_PROGRESS
        
        await self.session.commit()
        await self.session.refresh(task)
        return task
    
    async def cancel_task(self, task_id: int, user_id: int) -> Optional[Task]:
        """Отмена задачи"""
        task = await self.get_task_by_id(task_id, user_id)
        if not task:
            return None
        
        task.status = TaskStatus.CANCELLED
        
        await self.session.commit()
        await self.session.refresh(task)
        return task
    
    async def get_overdue_tasks(self, user_id: int) -> List[Task]:
        """Получение просроченных задач"""
        today = date.today()
        
        result = await self.session.execute(
            select(Task).where(
                and_(
                    Task.user_id == user_id,
                    Task.due_date < today,
                    Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])
                )
            )
        )
        return list(result.scalars().all())
    
    async def get_tasks_due_today(self, user_id: int) -> List[Task]:
        """Получение задач пользователя, срок которых истекает сегодня"""
        today = date.today()
        
        result = await self.session.execute(
            select(Task).where(
                and_(
                    Task.user_id == user_id,
                    Task.due_date == today,
                    Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS])  # Только невыполненные задачи
                )
            ).order_by(Task.priority.desc())
        )
        return list(result.scalars().all())
    
    # Методы для работы с категориями
    async def create_category(self, user_id: int, name: str, color: str = "#808080") -> TaskCategory:
        """Создание новой категории задач"""
        category = TaskCategory(
            user_id=user_id,
            name=name,
            color=color
        )
        
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def get_user_categories(self, user_id: int) -> List[TaskCategory]:
        """Получение всех категорий пользователя"""
        result = await self.session.execute(
            select(TaskCategory).where(TaskCategory.user_id == user_id)
            .order_by(TaskCategory.name)
        )
        return list(result.scalars().all())

    async def get_category_by_id(self, category_id: int, user_id: int) -> Optional[TaskCategory]:
        """Получение категории по ID"""
        result = await self.session.execute(
            select(TaskCategory).where(
                and_(
                    TaskCategory.id == category_id,
                    TaskCategory.user_id == user_id
                )
            )
        )
        return result.scalars().first()

    async def update_category(self, category_id: int, user_id: int, name: Optional[str] = None, 
                            color: Optional[str] = None) -> Optional[TaskCategory]:
        """Обновление категории"""
        category = await self.get_category_by_id(category_id, user_id)
        if not category:
            return None
        
        if name is not None:
            category.name = name
        if color is not None:
            category.color = color
        
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def delete_category(self, category_id: int, user_id: int) -> bool:
        """Удаление категории (задачи категории остаются, но без категории)"""
        category = await self.get_category_by_id(category_id, user_id)
        if not category:
            return False
        
        # Очищаем связь задач с этой категорией
        tasks = await self.session.execute(
            select(Task).where(Task.category_id == category_id)
        )
        for task in tasks.scalars():
            task.category_id = None
        
        await self.session.delete(category)
        await self.session.commit()
        return True

    async def get_tasks_by_category(self, user_id: int, category_id: Optional[int]) -> List[Task]:
        """Получение задач по категории"""
        query = select(Task).where(Task.user_id == user_id)
        
        if category_id is None:
            # Задачи без категории
            query = query.where(Task.category_id.is_(None))
        else:
            # Задачи с указанной категорией
            query = query.where(Task.category_id == category_id)
        
        result = await self.session.execute(query.order_by(Task.due_date, Task.priority.desc()))
        return list(result.scalars().all())

    async def get_category_stats(self, user_id: int) -> List[Tuple[Optional[TaskCategory], int, int]]:
        """Получение статистики по категориям: категория, общее количество задач, количество выполненных"""
        stats = []
        
        # Получаем категории пользователя
        categories = await self.get_user_categories(user_id)
        
        # Для каждой категории считаем статистику
        for category in categories:
            tasks = await self.get_tasks_by_category(user_id, category.id)
            total = len(tasks)
            completed = sum(1 for task in tasks if task.status == TaskStatus.DONE)
            stats.append((category, total, completed))
        
        # Добавляем статистику по задачам без категории
        tasks_no_category = await self.get_tasks_by_category(user_id, None)
        total_no_category = len(tasks_no_category)
        completed_no_category = sum(1 for task in tasks_no_category if task.status == TaskStatus.DONE)
        stats.append((None, total_no_category, completed_no_category))
        
        return stats 