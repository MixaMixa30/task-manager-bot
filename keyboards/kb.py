from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from typing import List, Optional

from database.models import TaskPriority, TaskStatus, Task, TaskCategory
from utils.helpers import get_priority_emoji, get_status_emoji


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура для бота"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📝 Мои задачи"),
        KeyboardButton(text="➕ Создать задачу"),
    )
    builder.row(
        KeyboardButton(text="🏆 Достижения"),
        KeyboardButton(text="📊 Статистика"),
    )
    builder.row(KeyboardButton(text="ℹ️ Помощь"))
    
    return builder.as_markup(resize_keyboard=True)


def get_task_priority_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора приоритета задачи"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⚪ Низкий", callback_data=f"priority:{TaskPriority.LOW.value}"),
        InlineKeyboardButton(text="🔵 Средний", callback_data=f"priority:{TaskPriority.MEDIUM.value}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔴 Высокий", callback_data=f"priority:{TaskPriority.HIGH.value}"),
        InlineKeyboardButton(text="⚡ Критический", callback_data=f"priority:{TaskPriority.CRITICAL.value}"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="cancel"))
    
    return builder.as_markup()


def get_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для действий с задачей"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Выполнить", callback_data=f"task:complete:{task_id}"),
        InlineKeyboardButton(text="🔄 В процессе", callback_data=f"task:progress:{task_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data=f"task:edit:{task_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"task:cancel:{task_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"task:delete:{task_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="tasks:list"),
    )
    
    return builder.as_markup()


def get_tasks_filter_keyboard(categories: List[TaskCategory] = None) -> InlineKeyboardMarkup:
    """Клавиатура для фильтрации задач по статусу и категориям"""
    builder = InlineKeyboardBuilder()
    
    # Фильтры по статусу
    builder.row(
        InlineKeyboardButton(text="Все", callback_data="tasks:filter:all"),
        InlineKeyboardButton(text="Активные", callback_data=f"tasks:filter:{TaskStatus.TODO.value},{TaskStatus.IN_PROGRESS.value}"),
    )
    builder.row(
        InlineKeyboardButton(text="Выполненные", callback_data=f"tasks:filter:{TaskStatus.DONE.value}"),
        InlineKeyboardButton(text="Просроченные", callback_data="tasks:filter:overdue"),
    )
    
    # Если есть категории, добавляем их как отдельную группу фильтров
    if categories:
        # Заголовок для секции категорий
        builder.row(InlineKeyboardButton(text="📂 Фильтр по категориям:", callback_data="ignore"))
        
        # Добавляем категории по 2 в ряд (или по 1, если категория с длинным названием)
        temp_row = []
        for category in categories:
            # Ограничиваем длину названия категории для кнопки
            cat_name = (category.name[:12] + '..') if len(category.name) > 14 else category.name
            button = InlineKeyboardButton(
                text=f"📂 {cat_name}", 
                callback_data=f"tasks:filter:category:{category.id}"
            )
            
            temp_row.append(button)
            if len(temp_row) == 2:
                builder.row(*temp_row)
                temp_row = []
        
        # Добавляем оставшиеся кнопки, если есть
        if temp_row:
            builder.row(*temp_row)
        
        # Кнопка для задач без категории
        builder.row(InlineKeyboardButton(
            text="📂 Без категории", 
            callback_data="tasks:filter:category:none"
        ))
    
    # Кнопка управления категориями
    builder.row(InlineKeyboardButton(
        text="⚙️ Управление категориями", 
        callback_data="categories:manage"
    ))
    
    return builder.as_markup()


def get_tasks_inline_keyboard(tasks: List[Task]) -> InlineKeyboardMarkup:
    """Генерация инлайн-клавиатуры со списком задач"""
    builder = InlineKeyboardBuilder()
    
    if not tasks:
        # Можно добавить кнопку "Создать задачу" прямо сюда, если список пуст
        # builder.add(InlineKeyboardButton(text="➕ Создать первую задачу", callback_data="create_task_inline"))
        pass # Или просто возвращаем пустую клавиатуру
    else:
        for task in tasks:
            priority_emoji = get_priority_emoji(task.priority)
            status_emoji = get_status_emoji(task.status)
            
            # Добавляем индикатор категории, если есть
            category_indicator = ""
            if hasattr(task, 'category') and task.category:
                category_indicator = f"📂 "
            
            # Обрезаем длинные названия для кнопки
            title_short = (task.title[:25] + '...') if len(task.title) > 28 else task.title
            
            # Создаем кнопку для каждой задачи
            builder.row(InlineKeyboardButton(
                text=f"{status_emoji} {priority_emoji} {category_indicator}{title_short}", 
                callback_data=f"task:view:{task.id}" # callback для просмотра задачи
            ))
            
    # Добавляем кнопки фильтрации снизу
    builder.row(
        InlineKeyboardButton(text="Все", callback_data="tasks:filter:all"),
        InlineKeyboardButton(text="Активные", callback_data=f"tasks:filter:{TaskStatus.TODO.value},{TaskStatus.IN_PROGRESS.value}"),
    )
    builder.row(
        InlineKeyboardButton(text="Выполненные", callback_data=f"tasks:filter:{TaskStatus.DONE.value}"),
        InlineKeyboardButton(text="Просроченные", callback_data="tasks:filter:overdue"),
    )
    
    # Кнопка для доступа к фильтрам по категориям
    builder.row(InlineKeyboardButton(
        text="📂 Фильтр по категориям", 
        callback_data="tasks:show_category_filters"
    ))
    
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def get_confirmation_keyboard(action: str, entity_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения действия"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}:{entity_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="cancel"),
    )
    return builder.as_markup()


def get_edit_task_field_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора поля задачи для редактирования"""
    builder = InlineKeyboardBuilder()
    # Добавляем task_id в callback_data, чтобы сохранить его при выборе поля
    builder.row(InlineKeyboardButton(text="📝 Название", callback_data=f"edit:field:title:{task_id}"))
    builder.row(InlineKeyboardButton(text="📋 Описание", callback_data=f"edit:field:description:{task_id}"))
    builder.row(InlineKeyboardButton(text="🎯 Приоритет", callback_data=f"edit:field:priority:{task_id}"))
    builder.row(InlineKeyboardButton(text="📅 Срок выполнения", callback_data=f"edit:field:due_date:{task_id}"))
    builder.row(InlineKeyboardButton(text="📂 Категория", callback_data=f"edit:field:category:{task_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к задаче", callback_data=f"task:view:{task_id}")) # Кнопка возврата к просмотру задачи
    
    return builder.as_markup()


# Новые клавиатуры для категорий
def get_category_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления категориями"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Создать категорию", callback_data="categories:create"))
    builder.row(InlineKeyboardButton(text="📋 Мои категории", callback_data="categories:list"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к задачам", callback_data="tasks:list"))
    return builder.as_markup()


def get_category_selection_keyboard(categories: List[TaskCategory], task_id: Optional[int] = None, 
                                   include_cancel: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура для выбора категории при создании/редактировании задачи"""
    builder = InlineKeyboardBuilder()
    
    if categories:
        for category in categories:
            # Ограничиваем длину названия категории
            cat_name = (category.name[:18] + '..') if len(category.name) > 20 else category.name
            
            # Формируем callback_data в зависимости от контекста
            callback_data = f"category:select:{category.id}"
            if task_id:
                callback_data = f"task:{task_id}:set_category:{category.id}" 
                
            builder.row(InlineKeyboardButton(text=f"📂 {cat_name}", callback_data=callback_data))
    
    # Добавляем кнопку "Без категории"
    callback_data = "category:select:none"
    if task_id:
        callback_data = f"task:{task_id}:set_category:none"
    
    builder.row(InlineKeyboardButton(text="🚫 Без категории", callback_data=callback_data))
    
    # Опционально добавляем кнопку отмены
    if include_cancel:
        callback_data = "cancel"
        if task_id:
            callback_data = f"task:view:{task_id}"
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data))
    
    return builder.as_markup()


def get_category_action_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с категорией"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Изменить название", callback_data=f"category:edit:name:{category_id}"),
        InlineKeyboardButton(text="🎨 Изменить цвет", callback_data=f"category:edit:color:{category_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"category:delete:{category_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="categories:list")
    )
    return builder.as_markup()


def get_categories_list_keyboard(categories: List[TaskCategory]) -> InlineKeyboardMarkup:
    """Клавиатура со списком категорий для управления"""
    builder = InlineKeyboardBuilder()
    
    if not categories:
        # Если категорий нет
        builder.row(InlineKeyboardButton(text="➕ Создать первую категорию", callback_data="categories:create"))
    else:
        for category in categories:
            # Ограничиваем длину названия
            cat_name = (category.name[:18] + '..') if len(category.name) > 20 else category.name
            builder.row(InlineKeyboardButton(
                text=f"📂 {cat_name}", 
                callback_data=f"category:view:{category.id}"
            ))
    
    builder.row(InlineKeyboardButton(text="➕ Новая категория", callback_data="categories:create"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="categories:manage"))
    
    return builder.as_markup()


def get_color_selection_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора цвета категории"""
    builder = InlineKeyboardBuilder()
    colors = [
        ("🔴 Красный", "#FF0000"),
        ("🟠 Оранжевый", "#FFA500"),
        ("🟡 Желтый", "#FFFF00"),
        ("🟢 Зеленый", "#00FF00"),
        ("🔵 Синий", "#0000FF"),
        ("🟣 Фиолетовый", "#800080"),
        ("⚫ Черный", "#000000"),
        ("⚪ Серый", "#808080")
    ]
    
    # Добавляем по 2 цвета в ряд
    for i in range(0, len(colors), 2):
        row = []
        for j in range(2):
            if i + j < len(colors):
                name, hex_code = colors[i + j]
                row.append(InlineKeyboardButton(
                    text=name,
                    callback_data=f"category:{category_id}:set_color:{hex_code}"
                ))
        builder.row(*row)
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"category:view:{category_id}"))
    
    return builder.as_markup() 