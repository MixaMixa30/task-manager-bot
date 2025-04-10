from datetime import date, timedelta
from typing import List, Optional

from database.models import Task, TaskPriority, TaskStatus
from services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession


def get_priority_emoji(priority: TaskPriority) -> str:
    """Получение эмодзи для приоритета задачи"""
    if priority == TaskPriority.LOW:
        return "⚪"
    elif priority == TaskPriority.MEDIUM:
        return "🔵"
    elif priority == TaskPriority.HIGH:
        return "🔴"
    elif priority == TaskPriority.CRITICAL:
        return "⚡"
    return "⚪"


def get_status_emoji(status: TaskStatus) -> str:
    """Получение эмодзи для статуса задачи"""
    if status == TaskStatus.TODO:
        return "📝"
    elif status == TaskStatus.IN_PROGRESS:
        return "🔄"
    elif status == TaskStatus.DONE:
        return "✅"
    elif status == TaskStatus.CANCELLED:
        return "❌"
    return "📝"


def format_task_message(task: Task) -> str:
    """Форматирование сообщения для задачи"""
    priority_emoji = get_priority_emoji(task.priority)
    status_emoji = get_status_emoji(task.status)
    
    status_names = {
        TaskStatus.TODO: "Ожидает выполнения",
        TaskStatus.IN_PROGRESS: "В процессе",
        TaskStatus.DONE: "Выполнено",
        TaskStatus.CANCELLED: "Отменено"
    }
    
    priority_names = {
        TaskPriority.LOW: "Низкий",
        TaskPriority.MEDIUM: "Средний",
        TaskPriority.HIGH: "Высокий",
        TaskPriority.CRITICAL: "Критический"
    }
    
    # Форматируем дату выполнения, если она есть
    due_date_str = f"\n📅 <b>Срок:</b> {task.due_date.strftime('%d.%m.%Y')}" if task.due_date else ""
    
    # Форматируем описание, если оно есть
    description_str = f"\n\n<i>{task.description}</i>" if task.description else ""
    
    # Форматируем дату выполнения, если задача выполнена
    completed_str = ""
    if task.status == TaskStatus.DONE and task.completed_at:
        completed_str = f"\n✨ <b>Выполнено:</b> {task.completed_at.strftime('%d.%m.%Y %H:%M')}"
    
    # Проверяем, просрочена ли задача
    overdue_str = ""
    if task.due_date and task.due_date < date.today() and task.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS]:
        overdue_str = "\n⚠️ <b>Просрочено!</b>"
    
    # Проверяем наличие категории
    category_str = ""
    if hasattr(task, 'category') and task.category:
        category_str = f"\n📂 <b>Категория:</b> {task.category.name}"
    
    return (
        f"<b>Квест #{task.id}: {task.title}</b>{description_str}\n\n"
        f"{status_emoji} <b>Статус:</b> {status_names.get(task.status, 'Неизвестно')}\n"
        f"{priority_emoji} <b>Приоритет:</b> {priority_names.get(task.priority, 'Стандартный')}"
        f"{due_date_str}"
        f"{category_str}"
        f"{completed_str}"
        f"{overdue_str}\n"
        f"💪 <b>Награда:</b> {task.xp_reward} XP"
    )


def format_tasks_list(tasks: List[Task]) -> List[str]:
    """Форматирование списка задач"""
    if not tasks:
        return ["У тебя пока нет задач. Создай первую задачу!"]
    
    # Разбиваем задачи на страницы по 5 задач
    tasks_per_page = 5
    pages = []
    
    for i in range(0, len(tasks), tasks_per_page):
        page_tasks = tasks[i:i+tasks_per_page]
        page_text = ""
        
        for task in page_tasks:
            priority_emoji = get_priority_emoji(task.priority)
            status_emoji = get_status_emoji(task.status)
            
            # Короткая информация о задаче
            due_date_str = f" • 📅 {task.due_date.strftime('%d.%m.%Y')}" if task.due_date else ""
            
            # Добавляем информацию о категории
            category_str = ""
            if hasattr(task, 'category') and task.category:
                category_str = f" • 📂 {task.category.name}"
            
            # Отмечаем просроченные задачи
            overdue_mark = " ⚠️" if task.due_date and task.due_date < date.today() and task.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS] else ""
            
            page_text += (
                f"{status_emoji} <b>#{task.id}: {task.title}</b>{overdue_mark}\n"
                f"{priority_emoji} {task.priority.value.capitalize()}{due_date_str}{category_str} • 💪 {task.xp_reward} XP\n\n"
            )
        
        pages.append(page_text)
    
    return pages


def is_overdue(task: Task) -> bool:
    """Проверка, является ли задача просроченной"""
    if not task.due_date:
        return False
    
    return task.due_date < date.today() and task.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS]


def format_user_stats(stats: dict) -> str:
    """Форматирование статистики пользователя"""
    xp_percent = int((stats["experience"] / stats["next_level_xp"]) * 100) if stats["next_level_xp"] > 0 else 0
    
    # Создаем прогресс-бар
    progress_bar_length = 10
    filled_blocks = int(xp_percent / 100 * progress_bar_length)
    progress_bar = "■" * filled_blocks + "□" * (progress_bar_length - filled_blocks)
    
    return (
        f"📊 <b>Журнал приключений</b>\n\n"
        f"🏆 <b>Уровень героя:</b> {stats['level']}\n"
        f"✨ <b>Опыт:</b> {stats['experience']}/{stats['next_level_xp']} XP\n"
        f"[{progress_bar}] {xp_percent}%\n\n"
        f"✅ <b>Выполненные квесты:</b> {stats['completed_tasks']}\n\n"
        f"Продолжай выполнять задания, чтобы получать опыт и открывать новые достижения!"
    )


def format_achievement(achievement_name: str, achievement_description: str, is_unlocked: bool) -> str:
    """Форматирование достижения"""
    status_emoji = "🌟" if is_unlocked else "🔒"
    
    if is_unlocked:
        return f"{status_emoji} <b>{achievement_name}</b>\n<i>{achievement_description}</i>"
    else:
        return f"{status_emoji} <b>{achievement_name}</b>\n<i>{achievement_description}</i>"


def get_date_range(days: int = 7) -> tuple:
    """Получение диапазона дат для статистики"""
    today = date.today()
    start_date = today - timedelta(days=days-1)
    return start_date, today


async def get_user_id_by_tg_id(session: AsyncSession, tg_id: int) -> int:
    """Получение ID пользователя из БД по Telegram ID"""
    user_service = UserService(session)
    user = await user_service.get_user_by_tg_id(tg_id)
    return user.id if user else None 