from datetime import datetime, date
from enum import Enum
from typing import List, Optional

from sqlalchemy import String, Integer, DateTime, Date, Boolean, ForeignKey, Text, Enum as SQLAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class TaskPriority(str, Enum):
    """Перечисление для приоритетов задач"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Перечисление для статусов задач"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Статистика пользователя
    level: Mapped[int] = mapped_column(Integer, default=1)
    experience: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    
    # Связи
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    achievements: Mapped[List["UserAchievement"]] = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    categories: Mapped[List["TaskCategory"]] = relationship("TaskCategory", back_populates="user", cascade="all, delete-orphan")


class Task(Base):
    """Модель задачи"""
    __tablename__ = "tasks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(SQLAEnum(TaskPriority), default=TaskPriority.MEDIUM)
    status: Mapped[TaskStatus] = mapped_column(SQLAEnum(TaskStatus), default=TaskStatus.TODO)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("task_categories.id", ondelete="SET NULL"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Для системы мотивации
    xp_reward: Mapped[int] = mapped_column(Integer, default=10)  # Сколько опыта дается за выполнение
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="tasks")
    category: Mapped[Optional["TaskCategory"]] = relationship("TaskCategory", back_populates="tasks")


class Achievement(Base):
    """Модель достижения"""
    __tablename__ = "achievements"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text)
    
    # Условия получения
    condition_type: Mapped[str] = mapped_column(String(50))  # tasks_count, streak_days и т.д.
    condition_value: Mapped[int] = mapped_column(Integer)  # Сколько нужно выполнить условие
    
    # Награда
    xp_reward: Mapped[int] = mapped_column(Integer, default=50)
    
    # Связи
    users: Mapped[List["UserAchievement"]] = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    """Модель для связи пользователя и достижений"""
    __tablename__ = "user_achievements"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    achievement_id: Mapped[int] = mapped_column(Integer, ForeignKey("achievements.id"), index=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="achievements")
    achievement: Mapped["Achievement"] = relationship("Achievement", back_populates="users")


class TaskCategory(Base):
    """Модель категории задач"""
    __tablename__ = "task_categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    color: Mapped[str] = mapped_column(String(20), default="#808080")  # Цвет в HEX формате
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="categories")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="category") 