from datetime import datetime, date
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import TaskPriority, TaskStatus, User
from keyboards.kb import (
    get_main_keyboard, get_task_priority_keyboard, get_task_actions_keyboard,
    get_tasks_filter_keyboard, get_cancel_keyboard, get_confirmation_keyboard,
    get_tasks_inline_keyboard, get_edit_task_field_keyboard, get_category_selection_keyboard
)
from services.task_service import TaskService
from services.user_service import UserService
from services.achievement_service import AchievementService
from utils.helpers import format_task_message, get_user_id_by_tg_id


# Создаем класс состояний FSM для создания задачи
class TaskForm(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_priority = State()
    waiting_for_due_date = State()
    waiting_for_category = State()


# Создаем класс состояний FSM для редактирования задачи
class EditTaskForm(StatesGroup):
    choosing_field = State() # Состояние выбора поля для редактирования
    waiting_for_new_title = State()
    waiting_for_new_description = State()
    waiting_for_new_priority = State()
    waiting_for_new_due_date = State()


# Создаем роутер для обработки задач
router = Router()


# Обработчики команд
@router.message(Command("tasks"))
async def cmd_tasks(message: Message, session: AsyncSession):
    """Обработчик команды /tasks"""
    task_service = TaskService(session)
    tasks = await task_service.get_user_tasks(
        user_id=(await get_user_id_by_tg_id(session, message.from_user.id))
    )
    
    # Вместо форматирования списка задач, используем инлайн клавиатуру
    reply_markup = get_tasks_inline_keyboard(tasks)
    
    if tasks:
        await message.answer(
            "📝 <b>Твои квесты (нажми для просмотра):</b>",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        await message.answer(
            "📭 <b>У тебя пока нет активных квестов!</b>\n\n"
            "Самое время начать свое приключение и создать первую задачу. "
            "Нажми на кнопку <b>➕ Создать задачу</b>, чтобы сделать первый шаг к продуктивности!",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )


@router.message(F.text == "📝 Мои задачи")
async def show_tasks(message: Message, session: AsyncSession):
    """Обработчик кнопки 'Мои задачи'"""
    await cmd_tasks(message, session)


@router.message(F.text == "➕ Создать задачу")
async def create_task_start(message: Message, state: FSMContext):
    """Обработчик кнопки 'Создать задачу'"""
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_creation"))
    
    await message.answer(
        "✨ <b>Создание нового квеста!</b>\n\n"
        "📝 Введи название задачи, которую хочешь выполнить:\n\n"
        "<i>Например: «Закончить отчет» или «Пробежка в парке»</i>",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await state.set_state(TaskForm.waiting_for_title)


@router.callback_query(F.data == "cancel_creation")
async def cancel_task_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания задачи"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Создание задачи отменено. Возвращайся, когда будешь готов!",
        reply_markup=None
    )
    # Отправляем основную клавиатуру
    await callback.message.answer("Что будем делать дальше?", reply_markup=get_main_keyboard())
    await callback.answer()


@router.message(TaskForm.waiting_for_title)
async def process_task_title(message: Message, state: FSMContext):
    """Обработка названия задачи"""
    if not message.text or not message.text.strip():
        await message.answer(
            "❌ <b>Название не может быть пустым</b>\n\n"
            "Пожалуйста, введите название задачи:",
            parse_mode="HTML"
        )
        return
        
    if len(message.text) > 200:
        await message.answer(
            "❌ <b>Название слишком длинное</b>\n\n"
            "Максимальная длина — 200 символов. Пожалуйста, сократи название задачи:",
            parse_mode="HTML"
        )
        return
    
    # Сохраняем название задачи
    await state.update_data(title=message.text.strip())
    
    # Создаем клавиатуру с кнопками для пропуска и отмены
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip_description"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_creation")
    )
    
    await message.answer(
        "✅ <b>Отличное название!</b>\n\n"
        "📋 Теперь добавь описание задачи или детали:\n\n"
        "<i>Можешь указать подробности или просто нажать кнопку «Пропустить»</i>",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await state.set_state(TaskForm.waiting_for_description)


@router.callback_query(TaskForm.waiting_for_description, F.data == "skip_description")
async def skip_description(callback: CallbackQuery, state: FSMContext):
    """Пропуск описания задачи"""
    await state.update_data(description=None)
    
    await callback.message.edit_text(
        "✅ <b>Описание пропущено</b>\n\n"
        "🎯 Выбери приоритет для своей задачи:",
        parse_mode="HTML",
        reply_markup=get_task_priority_keyboard()
    )
    await state.set_state(TaskForm.waiting_for_priority)
    await callback.answer()


@router.message(TaskForm.waiting_for_description)
async def process_task_description(message: Message, state: FSMContext):
    """Обработка описания задачи"""
    await state.update_data(description=message.text)
    
    await message.answer(
        "✅ <b>Описание добавлено!</b>\n\n"
        "🎯 Выбери приоритет для своей задачи:",
        parse_mode="HTML",
        reply_markup=get_task_priority_keyboard()
    )
    await state.set_state(TaskForm.waiting_for_priority)


@router.message(TaskForm.waiting_for_priority)
async def process_task_priority(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка приоритета задачи"""
    if not message.text or message.text not in ["1", "2", "3", "4"]:
        await message.answer(
            "❌ <b>Неверный приоритет</b>\n\n"
            "Пожалуйста, выбери приоритет цифрой от 1 до 4:",
            parse_mode="HTML",
            reply_markup=get_task_priority_keyboard()
        )
        return

    # Преобразуем текст в приоритет
    priority_map = {
        "1": TaskPriority.LOW,
        "2": TaskPriority.MEDIUM,
        "3": TaskPriority.HIGH,
        "4": TaskPriority.CRITICAL
    }
    priority = priority_map[message.text]
    await state.update_data(priority=priority)

    # Получаем категории пользователя для выбора
    user_id = await get_user_id_by_tg_id(session, message.from_user.id)
    if not user_id:
        logger.error(f"Не удалось получить user_id для tg_id {message.from_user.id}")
        await message.answer(
            "❌ <b>Ошибка при создании задачи</b>\n\n"
            "Пожалуйста, начните сначала с команды /start",
            parse_mode="HTML"
        )
        return

    task_service = TaskService(session)
    try:
        categories = await task_service.get_user_categories(user_id)
        
        # Запрашиваем дату выполнения
        await message.answer(
            "📅 <b>Когда нужно выполнить квест?</b>\n\n"
            "Укажи дату в формате ДД.ММ.ГГГГ (например, 31.12.2024)\n"
            "или отправь 'пропустить', чтобы создать задачу без срока.",
            parse_mode="HTML"
        )
        await state.set_state(TaskForm.waiting_for_due_date)
        
    except Exception as e:
        logger.error(f"Ошибка при получении категорий: {e}")
        await message.answer(
            "❌ <b>Ошибка при получении категорий</b>\n\n"
            "Продолжим без выбора категории.",
            parse_mode="HTML"
        )
        await state.update_data(category_id=None)
        await state.set_state(TaskForm.waiting_for_due_date)


@router.callback_query(TaskForm.waiting_for_due_date, F.data == "skip_due_date")
async def skip_due_date(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Пропуск даты выполнения"""
    await state.update_data(due_date=None)
    
    # Получаем категории пользователя для выбора
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    task_service = TaskService(session)
    categories = await task_service.get_user_categories(user_id)
    
    if categories:
        await callback.message.edit_text(
            "✅ <b>Срок выполнения пропущен</b>\n\n"
            "📂 Выбери категорию для задачи или пропусти этот шаг:",
            parse_mode="HTML",
            reply_markup=get_category_selection_keyboard(categories, None, True)
        )
        await state.set_state(TaskForm.waiting_for_category)
    else:
        # Если у пользователя нет категорий, пропускаем этот шаг
        await state.update_data(category_id=None)
        await create_task_final(callback.message, state, session)
    
    await callback.answer()


@router.message(TaskForm.waiting_for_due_date)
async def process_task_due_date(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка даты выполнения задачи"""
    if message.text and message.text.lower() in ["нет", "no", "отмена", "cancel", "пропустить", "skip", "-"]:
        # Пользователь решил пропустить указание даты
        await state.update_data(due_date=None)
        
        # Переходим к выбору категории
        user_id = await get_user_id_by_tg_id(session, message.from_user.id)
        task_service = TaskService(session)
        categories = await task_service.get_user_categories(user_id)
        
        if categories:
            await message.answer(
                "✅ <b>Срок выполнения не указан</b>\n\n"
                "📂 Выбери категорию для задачи или пропусти этот шаг:",
                parse_mode="HTML",
                reply_markup=get_category_selection_keyboard(categories, None, True)
            )
            await state.set_state(TaskForm.waiting_for_category)
        else:
            # Если у пользователя нет категорий, пропускаем этот шаг
            await state.update_data(category_id=None)
            await create_task_final(message, state, session)
        
        return
    
    try:
        # Пытаемся преобразовать текст в дату, пробуем несколько форматов
        due_date = None
        date_formats = ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"]
        
        for date_format in date_formats:
            try:
                due_date = datetime.strptime(message.text, date_format).date()
                break
            except ValueError:
                continue
        
        if due_date is None:
            raise ValueError("Неверный формат даты")
        
        # Проверяем, что дата не в прошлом
        if due_date < date.today():
            await message.answer(
                "❌ <b>Дата не может быть в прошлом</b>\n\n"
                "Укажи будущую дату в формате ДД.ММ.ГГГГ или пришли 'пропустить', чтобы создать задачу без срока:",
                parse_mode="HTML"
            )
            return
        
        # Сохраняем дату
        await state.update_data(due_date=due_date)
        
        # Получаем категории пользователя для выбора
        user_id = await get_user_id_by_tg_id(session, message.from_user.id)
        task_service = TaskService(session)
        categories = await task_service.get_user_categories(user_id)
        
        if categories:
            await message.answer(
                f"✅ <b>Срок выполнения установлен:</b> {due_date.strftime('%d.%m.%Y')}\n\n"
                "📂 Выбери категорию для задачи или пропусти этот шаг:",
                parse_mode="HTML",
                reply_markup=get_category_selection_keyboard(categories, None, True)
            )
            await state.set_state(TaskForm.waiting_for_category)
        else:
            # Если у пользователя нет категорий, пропускаем этот шаг
            await state.update_data(category_id=None)
            await create_task_final(message, state, session)
        
    except (ValueError, TypeError):
        await message.answer(
            "❌ <b>Неверный формат даты</b>\n\n"
            "Пожалуйста, используй формат ДД.ММ.ГГГГ (например, 31.12.2024) "
            "или пришли 'пропустить', чтобы создать задачу без срока:",
            parse_mode="HTML"
        )


@router.callback_query(TaskForm.waiting_for_category, F.data.startswith("category:select:"))
async def process_task_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка выбора категории"""
    category_data = callback.data.split(":")[2]
    
    if category_data == "none":
        await state.update_data(category_id=None)
    else:
        category_id = int(category_data)
        await state.update_data(category_id=category_id)
    
    await create_task_final(callback.message, state, session)
    await callback.answer()


async def create_task_final(message: Message, state: FSMContext, session: AsyncSession):
    """Финальный этап создания задачи"""
    # Получаем все данные формы
    data = await state.get_data()
    
    # Получаем ID пользователя из БД
    user_id = await get_user_id_by_tg_id(session, message.from_user.id)
    if not user_id:
        logger.error(f"Не удалось получить user_id для tg_id {message.from_user.id}")
        await message.answer(
            "❌ <b>Ошибка при создании задачи</b>\n\n"
            "Пожалуйста, попробуйте позже или используйте /start для переинициализации.",
            parse_mode="HTML"
        )
        return
    
    # Создаем объект TaskService для работы с задачами
    task_service = TaskService(session)
    
    try:
        # Создаем задачу
        task = await task_service.create_task(
            user_id=user_id,
            title=data["title"],
            description=data.get("description"),
            priority=TaskPriority(data["priority"]),
            due_date=data.get("due_date"),
            category_id=data.get("category_id")
        )
        
        # Дополнительно получаем категорию для отображения в сообщении
        if task.category_id:
            task.category = await task_service.get_category_by_id(task.category_id, user_id)
        
        # Очищаем состояние FSM
        await state.clear()
        
        # Отправляем сообщение о создании задачи
        await message.answer(
            f"🎉 <b>Квест создан!</b>\n\n{format_task_message(task)}",
            parse_mode="HTML",
            reply_markup=get_task_actions_keyboard(task.id)
        )
        
    except Exception as e:
        logger.error(f"Ошибка при создании задачи: {e}")
        await message.answer(
            "❌ <b>Ошибка при создании задачи</b>\n\n"
            "Пожалуйста, попробуйте еще раз.",
            parse_mode="HTML"
        )
        return


@router.callback_query(F.data.startswith("task:complete:"))
async def complete_task(callback: CallbackQuery, session: AsyncSession):
    """Обработчик кнопки 'Выполнить'"""
    task_id = int(callback.data.split(":")[2])
    
    # Получаем ID пользователя в БД
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    # Отмечаем задачу как выполненную
    task_service = TaskService(session)
    task = await task_service.complete_task(task_id, user_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Обновляем счетчик выполненных задач и добавляем опыт
    user_service = UserService(session)
    await user_service.update_completed_tasks_count(user_id)
    await user_service.add_experience(user_id, task.xp_reward)
    
    # Проверяем достижения
    achievement_service = AchievementService(session)
    new_achievements = await achievement_service.check_achievements(user_id)
    
    # Обновляем сообщение с задачей
    await callback.message.edit_text(
        f"🎉 <b>Квест выполнен!</b> +{task.xp_reward} XP\n\n{format_task_message(task)}",
        parse_mode="HTML"
    )
    
    # Если получены новые достижения, уведомляем пользователя
    if new_achievements:
        achievements_text = "\n".join([f"🏆 <b>{a.name}</b>: {a.description}" for a in new_achievements])
        total_xp = sum(a.xp_reward for a in new_achievements)
        
        await callback.message.answer(
            f"🌟 <b>Новые достижения разблокированы!</b>\n\n{achievements_text}\n\n"
            f"Бонусный опыт: <b>+{total_xp} XP</b>",
            parse_mode="HTML"
        )
    
    await callback.answer("✅ Задача выполнена! Отличная работа!")


@router.callback_query(F.data.startswith("task:progress:"))
async def set_task_in_progress(callback: CallbackQuery, session: AsyncSession):
    """Обработчик кнопки 'В процессе'"""
    task_id = int(callback.data.split(":")[2])
    
    # Получаем ID пользователя в БД
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    # Устанавливаем статус "в процессе"
    task_service = TaskService(session)
    task = await task_service.set_task_in_progress(task_id, user_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Обновляем сообщение с задачей
    await callback.message.edit_text(
        f"🔄 <b>Квест в процессе выполнения!</b>\n\n{format_task_message(task)}",
        parse_mode="HTML",
        reply_markup=get_task_actions_keyboard(task.id)
    )
    
    await callback.answer("Задача отмечена как 'В процессе'")


@router.callback_query(F.data.startswith("task:cancel:"))
async def cancel_task(callback: CallbackQuery, session: AsyncSession):
    """Обработчик кнопки 'Отменить'"""
    task_id = int(callback.data.split(":")[2])
    
    # Запрос подтверждения
    await callback.message.edit_text(
        "❓ <b>Уверен, что хочешь отменить этот квест?</b>\n\n"
        "Отмененные задачи будут сохранены в истории, но не принесут опыта.",
        parse_mode="HTML",
        reply_markup=get_confirmation_keyboard("cancel_task", task_id)
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:cancel_task:"))
async def confirm_cancel_task(callback: CallbackQuery, session: AsyncSession):
    """Подтверждение отмены задачи"""
    task_id = int(callback.data.split(":")[2])
    
    # Получаем ID пользователя в БД
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    # Отменяем задачу
    task_service = TaskService(session)
    task = await task_service.cancel_task(task_id, user_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Обновляем сообщение с задачей
    await callback.message.edit_text(
        f"❌ <b>Квест отменен</b>\n\n{format_task_message(task)}",
        parse_mode="HTML"
    )
    
    await callback.answer("Задача отменена")


@router.callback_query(F.data.startswith("task:delete:"))
async def delete_task(callback: CallbackQuery, session: AsyncSession):
    """Обработчик кнопки 'Удалить'"""
    task_id = int(callback.data.split(":")[2])
    
    # Запрос подтверждения
    await callback.message.edit_text(
        "⚠️ <b>Уверен, что хочешь удалить этот квест?</b>\n\n"
        "Это действие нельзя отменить, задача будет удалена навсегда.",
        parse_mode="HTML",
        reply_markup=get_confirmation_keyboard("delete_task", task_id)
    )
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:delete_task:"))
async def confirm_delete_task(callback: CallbackQuery, session: AsyncSession):
    """Подтверждение удаления задачи"""
    task_id = int(callback.data.split(":")[2])
    
    # Получаем ID пользователя в БД
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    # Удаляем задачу
    task_service = TaskService(session)
    success = await task_service.delete_task(task_id, user_id)
    
    if not success:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Обновляем сообщение
    await callback.message.edit_text("🗑️ <b>Квест удален</b>", parse_mode="HTML")
    
    await callback.answer("Задача удалена")


@router.callback_query(F.data.startswith("tasks:filter:"))
async def filter_tasks(callback: CallbackQuery, session: AsyncSession):
    """Обработчик фильтрации задач"""
    filter_data = callback.data.split(":")[2]
    
    # Получаем ID пользователя в БД
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    # Вынесем логику отображения в отдельную функцию или оставим здесь для простоты
    await show_filtered_tasks(callback, session, user_id, filter_data)


@router.callback_query(F.data == "tasks:list")
async def back_to_tasks_list(callback: CallbackQuery, session: AsyncSession):
    """Обработчик возврата к списку задач"""
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    # Убираем изменение callback.data
    # callback.data = "tasks:filter:all" 
    # Явно вызываем логику отображения всех задач
    await show_filtered_tasks(callback, session, user_id, "all") 


# Немного рефакторинга: выносим логику отображения задач
async def show_filtered_tasks(callback: CallbackQuery, session: AsyncSession, user_id: int, filter_data: str):
    """Отображает задачи пользователя согласно фильтру"""
    task_service = TaskService(session)
    tasks = []
    filter_name = "квесты"

    # Определяем, какие задачи показывать
    if filter_data == "all":
        tasks = await task_service.get_user_tasks(user_id)
        filter_name = "все квесты"
    elif filter_data == "overdue":
        tasks = await task_service.get_overdue_tasks(user_id)
        filter_name = "просроченные квесты"
    else:
        # Фильтр по статусам
        try:
            statuses = [TaskStatus(s) for s in filter_data.split(",")]
            tasks = await task_service.get_user_tasks(user_id, statuses)
            
            # Определяем название фильтра
            if len(statuses) == 1:
                status_names = {
                    TaskStatus.TODO: "ожидающие выполнения",
                    TaskStatus.IN_PROGRESS: "в процессе",
                    TaskStatus.DONE: "выполненные",
                    TaskStatus.CANCELLED: "отмененные"
                }
                filter_name = status_names.get(statuses[0], "квесты")
            else:
                # Если статусов несколько (TODO, IN_PROGRESS), то это 'активные'
                filter_name = "активные квесты"
        except ValueError:
            logger.error(f"Неверный формат фильтра статусов: {filter_data}")
            await callback.answer("Ошибка фильтрации", show_alert=True)
            return

    # Форматируем и отправляем список задач с инлайн-кнопками
    reply_markup = get_tasks_inline_keyboard(tasks)
    
    # Формируем заголовок
    header_text = f"📋 <b>Твои {filter_name}:</b>"
    if filter_data == "overdue" and tasks:
        header_text = "⏳ <b>Просроченные квесты:</b>\n\n"
        header_text += "<i>Не позволяй им накапливаться! Выполни их или отмени, чтобы двигаться дальше к новым свершениям!</i> 💪"
    elif not tasks:
        header_text = f"📭 <b>У тебя пока нет квестов в категории</b> «{filter_name}»"
    
    try:
        # Используем edit_text для обновления сообщения
        await callback.message.edit_text(
            header_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        await callback.answer() # Убираем часики у кнопки
    except Exception as e:
        logger.info(f"Не удалось изменить сообщение при фильтрации (возможно, оно не изменилось): {e}") 
        # Если изменить не удалось (например, сообщение идентично), просто отвечаем
        await callback.answer()


# Новый обработчик для просмотра задачи по кнопке
@router.callback_query(F.data.startswith("task:view:"))
async def view_task_details(callback: CallbackQuery, session: AsyncSession):
    """Обработчик нажатия на кнопку задачи для просмотра деталей"""
    task_id = int(callback.data.split(":")[2])
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    task_service = TaskService(session)
    task = await task_service.get_task_by_id(task_id, user_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Форматируем сообщение с деталями задачи
    task_message = format_task_message(task)
    
    # Получаем клавиатуру действий для этой задачи
    reply_markup = get_task_actions_keyboard(task.id)
    
    await callback.message.edit_text(
        task_message,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task:edit:"))
async def start_task_edit(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начало процесса редактирования задачи"""
    task_id = int(callback.data.split(":")[2])
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    task_service = TaskService(session)
    task = await task_service.get_task_by_id(task_id, user_id)
    
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    # Сохраняем ID задачи в состоянии FSM
    await state.update_data(edit_task_id=task_id)
    
    # Формируем сообщение с текущими данными и клавиатурой выбора поля
    edit_text = f"✏️ <b>Редактирование квеста #{task.id}</b>\n\n"
    edit_text += format_task_message(task)
    edit_text += "\n\n❓ Какое поле ты хочешь изменить?"
    
    reply_markup = get_edit_task_field_keyboard(task_id)
    
    await callback.message.edit_text(
        edit_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    await state.set_state(EditTaskForm.choosing_field)
    await callback.answer()


# Обработчик выбора поля "Название"
@router.callback_query(EditTaskForm.choosing_field, F.data.startswith("edit:field:title:"))
async def edit_task_title_start(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[3]) # Получаем task_id из callback_data
    await state.update_data(edit_task_id=task_id) # На всякий случай сохраняем еще раз
    
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_edit:{task_id}"))
    
    await callback.message.edit_text(
        "📝 Введи новое название задачи:", 
        reply_markup=kb.as_markup()
    )
    await state.set_state(EditTaskForm.waiting_for_new_title)
    await callback.answer()


# Обработка нового названия
@router.message(EditTaskForm.waiting_for_new_title)
async def process_new_task_title(message: Message, state: FSMContext, session: AsyncSession):
    if len(message.text) > 200:
        await message.answer(
            "❌ <b>Название слишком длинное</b> (макс. 200 символов). Попробуй еще раз:", 
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    task_id = data.get("edit_task_id")
    user_id = await get_user_id_by_tg_id(session, message.from_user.id)
    
    await update_task_field(state, session, user_id, task_id, {"title": message.text}, message)


# Обработчик выбора поля "Описание"
@router.callback_query(EditTaskForm.choosing_field, F.data.startswith("edit:field:description:"))
async def edit_task_description_start(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[3])
    await state.update_data(edit_task_id=task_id)
    
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🚫 Очистить описание", callback_data=f"edit:clear_description:{task_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_edit:{task_id}"),
    )
    
    await callback.message.edit_text(
        "📋 Введи новое описание задачи (или нажми 'Очистить'):",
        reply_markup=kb.as_markup()
    )
    await state.set_state(EditTaskForm.waiting_for_new_description)
    await callback.answer()


# Обработка нового описания (или его очистки)
@router.message(EditTaskForm.waiting_for_new_description)
async def process_new_task_description(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    task_id = data.get("edit_task_id")
    user_id = await get_user_id_by_tg_id(session, message.from_user.id)
    
    await update_task_field(state, session, user_id, task_id, {"description": message.text}, message)

@router.callback_query(EditTaskForm.waiting_for_new_description, F.data.startswith("edit:clear_description:"))
async def clear_new_task_description(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    task_id = int(callback.data.split(":")[2])
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    await update_task_field(state, session, user_id, task_id, {"description": None}, callback.message)
    await callback.answer("Описание очищено")


# Обработка нового приоритета
@router.callback_query(EditTaskForm.choosing_field, F.data.startswith("edit:field:priority:"))
async def edit_task_priority_start(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[3])
    await state.update_data(edit_task_id=task_id)
    
    # Используем ту же клавиатуру, что и при создании
    kb = get_task_priority_keyboard()
    # Добавляем кнопку отмены
    builder = InlineKeyboardBuilder.from_markup(kb)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_edit:{task_id}"))
    
    await callback.message.edit_text(
        "🎯 Выбери новый приоритет:", 
        reply_markup=builder.as_markup()
    )
    await state.set_state(EditTaskForm.waiting_for_new_priority)
    await callback.answer()


# Обработка нового приоритета
@router.callback_query(EditTaskForm.waiting_for_new_priority, F.data.startswith("priority:"))
async def process_new_task_priority(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    priority_value = TaskPriority(callback.data.split(":")[1])
    data = await state.get_data()
    task_id = data.get("edit_task_id")
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    # Приоритет также влияет на xp_reward и is_important
    task_service = TaskService(session)
    new_xp_reward = task_service._calculate_xp_reward(priority_value)
    is_important = priority_value == TaskPriority.HIGH
    
    update_data = {
        "priority": priority_value,
        "xp_reward": new_xp_reward,
        "is_important": is_important
    }
    
    await update_task_field(state, session, user_id, task_id, update_data, callback.message)
    await callback.answer("Приоритет обновлен")


# Обработка новой даты выполнения (или ее очистки)
@router.message(EditTaskForm.waiting_for_new_due_date)
async def process_new_task_due_date(message: Message, state: FSMContext, session: AsyncSession):
    try:
        due_date = datetime.strptime(message.text, "%d.%m.%Y").date()
        if due_date < date.today():
            await message.answer(
                "❌ <b>Дата не может быть в прошлом</b>. Укажи будущую дату (ДД.ММ.ГГГГ) или нажми 'Убрать срок':",
                parse_mode="HTML"
            )
            return
            
        data = await state.get_data()
        task_id = data.get("edit_task_id")
        user_id = await get_user_id_by_tg_id(session, message.from_user.id)
        
        await update_task_field(state, session, user_id, task_id, {"due_date": due_date}, message)
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат даты</b>. Используй ДД.ММ.ГГГГ (например, 01.12.2025) или нажми 'Убрать срок':",
            parse_mode="HTML"
        )

@router.callback_query(EditTaskForm.waiting_for_new_due_date, F.data.startswith("edit:clear_due_date:"))
async def clear_new_task_due_date(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    task_id = int(callback.data.split(":")[2])
    user_id = await get_user_id_by_tg_id(session, callback.from_user.id)
    
    await update_task_field(state, session, user_id, task_id, {"due_date": None}, callback.message)
    await callback.answer("Срок выполнения убран")


# --- Вспомогательная функция для обновления поля и завершения FSM ---

async def update_task_field(state: FSMContext, session: AsyncSession, user_id: int, task_id: int, update_data: dict, source_message: Message):
    """Обновляет поле задачи, сбрасывает состояние и показывает обновленную задачу."""
    task_service = TaskService(session)
    updated_task = await task_service.update_task(task_id, user_id, update_data)
    await state.clear()
    
    if updated_task:
        await source_message.edit_text(
            f"✅ Поле обновлено!\n\n{format_task_message(updated_task)}",
            parse_mode="HTML",
            reply_markup=get_task_actions_keyboard(task_id)
        )
    else:
        await source_message.edit_text("❌ Не удалось обновить задачу.")


# --- Обработчик отмены редактирования ---

@router.callback_query(F.data.startswith("cancel_edit:"))
async def cancel_edit_task(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Отмена текущего шага редактирования и возврат к просмотру задачи."""
    await state.clear()
    # Просто вызываем обработчик просмотра задачи, чтобы показать ее снова
    task_id = int(callback.data.split(":")[1])
    callback.data = f"task:view:{task_id}" 
    await view_task_details(callback, session)
    await callback.answer("Редактирование отменено")


# --- Конец блока редактирования задачи ---

async def get_user_id_by_tg_id(session: AsyncSession, tg_id: int) -> int:
    """Получение ID пользователя из БД по Telegram ID"""
    user_service = UserService(session)
    user = await user_service.get_user_by_tg_id(tg_id)
    return user.id if user else None 