import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from services.task_service import TaskService
from database.models import TaskCategory
from keyboards.kb import (
    get_category_management_keyboard, get_categories_list_keyboard,
    get_category_action_keyboard, get_color_selection_keyboard,
    get_tasks_filter_keyboard, get_category_selection_keyboard
)
from utils.helpers import get_user_id_by_tg_id

# Создаем роутер для обработчиков категорий
router = Router()
logger = logging.getLogger(__name__)

# Определяем FSM для создания и редактирования категорий
class CategoryForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_color = State()
    edit_name = State()


@router.callback_query(F.data == "categories:manage")
async def manage_categories(callback: CallbackQuery):
    """Обработчик кнопки управления категориями"""
    await callback.message.edit_text(
        "📁 <b>Управление категориями задач</b>\n\n"
        "Категории помогают организовать задачи по темам. "
        "Выбери действие:",
        parse_mode="HTML",
        reply_markup=get_category_management_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "categories:list")
async def show_categories_list(callback: CallbackQuery, session: AsyncSession):
    """Показывает список категорий пользователя"""
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    task_service = TaskService(session)
    
    categories = await task_service.get_user_categories(user_id)
    
    if not categories:
        await callback.message.edit_text(
            "📭 <b>У тебя пока нет категорий</b>\n\n"
            "Создай свою первую категорию, чтобы организовать задачи!",
            parse_mode="HTML",
            reply_markup=get_categories_list_keyboard(categories)
        )
    else:
        categories_text = "\n".join([
            f"📂 <b>{category.name}</b> - {len(await task_service.get_tasks_by_category(user_id, category.id))} задач"
            for category in categories
        ])
        
        await callback.message.edit_text(
            f"📁 <b>Твои категории:</b>\n\n{categories_text}",
            parse_mode="HTML",
            reply_markup=get_categories_list_keyboard(categories)
        )
    
    await callback.answer()


@router.callback_query(F.data == "categories:create")
async def create_category_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания новой категории"""
    await state.set_state(CategoryForm.waiting_for_name)
    
    await callback.message.edit_text(
        "🏷️ <b>Создание новой категории</b>\n\n"
        "Введи название для категории (максимум 50 символов):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CategoryForm.waiting_for_name)
async def process_category_name(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка названия новой категории"""
    if len(message.text) > 50:
        await message.answer(
            "❌ <b>Название слишком длинное</b> (макс. 50 символов). Попробуй еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(category_name=message.text)
    
    # Создаем категорию сразу с дефолтным цветом
    user_id = await get_user_id_by_tg_id(session, message.from_user.id)
    task_service = TaskService(session)
    
    category = await task_service.create_category(user_id, message.text)
    
    await state.clear()
    
    await message.answer(
        f"✅ <b>Категория '{category.name}' создана!</b>\n\n"
        f"Теперь ты можешь добавлять задачи в эту категорию при создании "
        f"или редактировании задачи.",
        parse_mode="HTML",
        reply_markup=get_category_action_keyboard(category.id)
    )


@router.callback_query(F.data.startswith("category:view:"))
async def view_category(callback: CallbackQuery, session: AsyncSession):
    """Просмотр категории и ее задач"""
    category_id = int(callback.data.split(":")[2])
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    task_service = TaskService(session)
    category = await task_service.get_category_by_id(category_id, user_id)
    
    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return
    
    # Получаем задачи категории
    tasks = await task_service.get_tasks_by_category(user_id, category_id)
    active_tasks = [t for t in tasks if t.status != "done" and t.status != "cancelled"]
    completed_tasks = [t for t in tasks if t.status == "done"]
    
    # Формируем текст
    message_text = (
        f"📂 <b>Категория: {category.name}</b>\n\n"
        f"🔢 Всего задач: <b>{len(tasks)}</b>\n"
        f"⏳ Активных: <b>{len(active_tasks)}</b>\n"
        f"✅ Выполнено: <b>{len(completed_tasks)}</b>\n\n"
        f"🎨 Цвет: <code>{category.color}</code>\n"
        f"🕒 Создана: {category.created_at.strftime('%d.%m.%Y')}"
    )
    
    await callback.message.edit_text(
        message_text,
        parse_mode="HTML",
        reply_markup=get_category_action_keyboard(category.id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("category:edit:name:"))
async def edit_category_name_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования названия категории"""
    category_id = int(callback.data.split(":")[3])
    await state.set_state(CategoryForm.edit_name)
    await state.update_data(category_id=category_id)
    
    await callback.message.edit_text(
        "🏷️ <b>Редактирование категории</b>\n\n"
        "Введи новое название для категории (максимум 50 символов):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CategoryForm.edit_name)
async def process_edit_category_name(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка нового названия категории"""
    if len(message.text) > 50:
        await message.answer(
            "❌ <b>Название слишком длинное</b> (макс. 50 символов). Попробуй еще раз:",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    category_id = data.get("category_id")
    user_id = await get_user_id_by_tg_id(session, message.from_user.id)
    
    task_service = TaskService(session)
    category = await task_service.update_category(category_id, user_id, name=message.text)
    
    await state.clear()
    
    if category:
        await message.answer(
            f"✅ <b>Категория переименована в '{category.name}'</b>",
            parse_mode="HTML",
            reply_markup=get_category_action_keyboard(category.id)
        )
    else:
        await message.answer(
            "❌ <b>Не удалось обновить категорию</b>",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("category:edit:color:"))
async def edit_category_color_start(callback: CallbackQuery):
    """Начало редактирования цвета категории"""
    category_id = int(callback.data.split(":")[3])
    
    await callback.message.edit_text(
        "🎨 <b>Выбери цвет для категории:</b>",
        parse_mode="HTML",
        reply_markup=get_color_selection_keyboard(category_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("category:"))
async def set_category_color(callback: CallbackQuery, session: AsyncSession):
    """Установка цвета категории"""
    parts = callback.data.split(":")
    if len(parts) >= 4 and parts[2] == "set_color":
        category_id = int(parts[1])
        color = parts[3]
        
        user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
        task_service = TaskService(session)
        
        category = await task_service.update_category(category_id, user_id, color=color)
        
        if category:
            await callback.answer(f"Цвет категории обновлен")
            # Вызываем обработчик просмотра категории, чтобы показать обновленную информацию
            callback.data = f"category:view:{category_id}"
            await view_category(callback, session)
        else:
            await callback.answer("❌ Не удалось обновить цвет категории", show_alert=True)


@router.callback_query(F.data.startswith("category:delete:"))
async def delete_category_confirm(callback: CallbackQuery):
    """Подтверждение удаления категории"""
    category_id = int(callback.data.split(":")[2])
    
    from keyboards.kb import get_confirmation_keyboard
    await callback.message.edit_text(
        "⚠️ <b>Уверен, что хочешь удалить эту категорию?</b>\n\n"
        "Задачи в категории останутся, но будут помечены как 'Без категории'.",
        parse_mode="HTML",
        reply_markup=get_confirmation_keyboard("delete_category", category_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:delete_category:"))
async def confirm_delete_category(callback: CallbackQuery, session: AsyncSession):
    """Подтверждение удаления категории"""
    category_id = int(callback.data.split(":")[2])
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    task_service = TaskService(session)
    success = await task_service.delete_category(category_id, user_id)
    
    if success:
        await callback.message.edit_text(
            "🗑️ <b>Категория удалена</b>",
            parse_mode="HTML",
            reply_markup=get_category_management_keyboard()
        )
        await callback.answer("Категория удалена")
    else:
        await callback.answer("❌ Не удалось удалить категорию", show_alert=True)


# Обработчик для фильтрации задач по категории
@router.callback_query(F.data.startswith("tasks:filter:category:"))
async def filter_tasks_by_category(callback: CallbackQuery, session: AsyncSession):
    """Фильтрация задач по категории"""
    category_data = callback.data.split(":")[3]
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    task_service = TaskService(session)
    
    if category_data == "none":
        # Задачи без категории
        tasks = await task_service.get_tasks_by_category(user_id, None)
        header = "📂 <b>Задачи без категории:</b>"
    else:
        # Задачи определенной категории
        category_id = int(category_data)
        category = await task_service.get_category_by_id(category_id, user_id)
        
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
            
        tasks = await task_service.get_tasks_by_category(user_id, category_id)
        header = f"📂 <b>Задачи категории '{category.name}':</b>"
    
    # Отображаем отфильтрованные задачи
    from keyboards.kb import get_tasks_inline_keyboard
    
    if not tasks:
        header = f"{header}\n\n📭 <b>В этой категории нет задач</b>"
    
    await callback.message.edit_text(
        header,
        parse_mode="HTML",
        reply_markup=get_tasks_inline_keyboard(tasks)
    )
    await callback.answer()


@router.callback_query(F.data == "tasks:show_category_filters")
async def show_category_filters(callback: CallbackQuery, session: AsyncSession):
    """Показывает фильтры по категориям"""
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    task_service = TaskService(session)
    
    categories = await task_service.get_user_categories(user_id)
    
    await callback.message.edit_text(
        "📂 <b>Фильтрация задач по категориям</b>\n\n"
        "Выбери категорию для отображения задач:",
        parse_mode="HTML",
        reply_markup=get_tasks_filter_keyboard(categories)
    )
    await callback.answer()


# Обработчики для выбора категории при редактировании задачи
@router.callback_query(F.data.startswith("edit:field:category:"))
async def edit_task_category_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало редактирования категории задачи"""
    task_id = int(callback.data.split(":")[3])
    await state.update_data(edit_task_id=task_id)
    
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    task_service = TaskService(session)
    
    categories = await task_service.get_user_categories(user_id)
    
    await callback.message.edit_text(
        "📂 <b>Выбери категорию для задачи:</b>",
        parse_mode="HTML",
        reply_markup=get_category_selection_keyboard(categories, task_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task:"))
async def set_task_category(callback: CallbackQuery, session: AsyncSession):
    """Установка категории для задачи"""
    parts = callback.data.split(":")
    if len(parts) >= 4 and parts[2] == "set_category":
        task_id = int(parts[1])
        category_data = parts[3]
        
        user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
        task_service = TaskService(session)
        
        if category_data == "none":
            # Убираем категорию
            update_data = {"category_id": None}
        else:
            # Устанавливаем категорию
            category_id = int(category_data)
            update_data = {"category_id": category_id}
        
        # Обновляем задачу
        updated_task = await task_service.update_task(task_id, user_id, update_data)
        
        if updated_task:
            # Вызываем обработчик просмотра задачи
            from handlers.tasks import view_task_details, format_task_message
            from keyboards.kb import get_task_actions_keyboard
            
            # Выводим сообщение об успешном обновлении
            category_text = "Без категории" if updated_task.category_id is None else f"{updated_task.category.name}"
            
            await callback.message.edit_text(
                f"✅ <b>Категория задачи обновлена:</b> {category_text}\n\n"
                f"{format_task_message(updated_task)}",
                parse_mode="HTML",
                reply_markup=get_task_actions_keyboard(task_id)
            )
            await callback.answer("Категория задачи обновлена")
        else:
            await callback.answer("❌ Не удалось обновить категорию задачи", show_alert=True) 