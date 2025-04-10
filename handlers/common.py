from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from keyboards.kb import get_main_keyboard
from services.user_service import UserService


# Создаем роутер для обработки общих команд
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    """Обработчик команды /start"""
    user_service = UserService(session)
    
    # Проверяем, существует ли пользователь, если нет - создаем
    user = await user_service.get_user_by_tg_id(message.from_user.id)
    if not user:
        user = await user_service.create_user(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
    
    # Приветственное сообщение
    await message.answer(
        f"🚀 <b>Добро пожаловать в TaskHero, {user.first_name}!</b>\n\n"
        "Я твой личный помощник по продуктивности, который превратит рутинные задачи в увлекательное приключение! ✨\n\n"
        "🎮 <b>TaskHero - это не просто планировщик:</b>\n"
        "• Создавай задачи и получай опыт за их выполнение\n"
        "• Повышай свой уровень и разблокируй достижения\n"
        "• Отслеживай прогресс и становись продуктивнее каждый день\n\n"
        "🎯 Готов стать героем своей продуктивности? Нажми <b>\"➕ Создать задачу\"</b> и начни свой путь к успеху!",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "🦸‍♂️ <b>Справочник героя продуктивности</b>\n\n"
        "🔍 <b>Основные команды:</b>\n"
        "• /start — Начать приключение\n"
        "• /help — Открыть справочник героя\n"
        "• /tasks — Управление квестами\n"
        "• /achievements — Книга достижений\n"
        "• /stats — Журнал героя\n\n"
        
        "💡 <b>Как пользоваться TaskHero:</b>\n"
        "1. Нажми <b>➕ Создать задачу</b> для добавления нового квеста\n"
        "2. Просматривай свои задачи в разделе <b>📝 Мои задачи</b>\n"
        "3. Выполняй задачи, получай опыт и открывай новые уровни\n"
        "4. Следи за своим прогрессом в разделе <b>📊 Статистика</b>\n\n"
        
        "🏆 <b>Система достижений:</b>\n"
        "• Каждая выполненная задача приближает тебя к новым достижениям\n"
        "• За достижения ты получаешь бонусный опыт\n"
        "• Разблокируй все достижения, чтобы стать настоящим героем продуктивности!\n\n"
        
        "Удачных приключений в мире продуктивности! 🌟"
    )
    
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_main_keyboard())


# Добавляем обработчик для кнопки "Помощь"
@router.message(F.text == "ℹ️ Помощь")
async def show_help_button(message: Message):
    """Обработчик кнопки 'ℹ️ Помощь'"""
    # Просто вызываем существующий обработчик команды /help
    await cmd_help(message)


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery):
    """Обработчик отмены действия"""
    await callback.message.delete()
    await callback.answer("Действие отменено") 