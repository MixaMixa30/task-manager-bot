from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Achievement
from keyboards.kb import get_main_keyboard
from services.achievement_service import AchievementService
from services.user_service import UserService
from utils.helpers import format_user_stats, format_achievement

# Создаем роутер для обработки достижений и статистики
router = Router()


@router.message(Command("achievements"))
async def cmd_achievements(message: Message, session: AsyncSession):
    """Обработчик команды /achievements"""
    # Получаем ID пользователя
    user_service = UserService(session)
    user = await user_service.get_user_by_tg_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        return
    
    # Получаем список достижений
    achievement_service = AchievementService(session)
    all_achievements = await achievement_service.get_all_achievements()
    user_achievements = await achievement_service.get_user_achievements(user.id)
    
    # Собираем ID достижений пользователя
    user_achievement_ids = [ua.achievement_id for ua in user_achievements]
    
    # Форматируем сообщение
    message_text = "🏆 <b>Книга достижений</b>\n\n"
    
    # Сначала показываем разблокированные достижения
    unlocked_achievements = []
    locked_achievements = []
    
    for achievement in all_achievements:
        is_unlocked = achievement.id in user_achievement_ids
        formatted = format_achievement(
            achievement.name,
            achievement.description,
            is_unlocked
        )
        
        if is_unlocked:
            unlocked_achievements.append(formatted)
        else:
            locked_achievements.append(formatted)
    
    # Добавляем разблокированные достижения
    if unlocked_achievements:
        message_text += "<b>Открытые достижения:</b>\n"
        message_text += "\n\n".join(unlocked_achievements)
        message_text += "\n\n"
    
    # Добавляем заблокированные достижения
    if locked_achievements:
        message_text += "<b>Предстоит открыть:</b>\n"
        message_text += "\n\n".join(locked_achievements)
        message_text += "\n\n"
    
    # Добавляем статистику открытых достижений
    unlocked_count = len(unlocked_achievements)
    total_count = len(all_achievements)
    progress_percent = int((unlocked_count / total_count) * 100) if total_count > 0 else 0
    
    # Создаем прогресс-бар
    progress_bar_length = 10
    filled_blocks = int(progress_percent / 100 * progress_bar_length)
    progress_bar = "■" * filled_blocks + "□" * (progress_bar_length - filled_blocks)
    
    message_text += f"<b>Прогресс:</b> {unlocked_count}/{total_count} ({progress_percent}%)\n"
    message_text += f"[{progress_bar}]"
    
    await message.answer(message_text, parse_mode="HTML", reply_markup=get_main_keyboard())


@router.message(F.text == "🏆 Достижения")
async def show_achievements(message: Message, session: AsyncSession):
    """Обработчик кнопки 'Достижения'"""
    await cmd_achievements(message, session)


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    """Обработчик команды /stats"""
    # Получаем статистику пользователя
    user_service = UserService(session)
    user = await user_service.get_user_by_tg_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        return
    
    stats = await user_service.get_user_stats(user.id)
    
    if not stats:
        await message.answer("❌ Не удалось получить статистику")
        return
    
    # Форматируем статистику
    stats_text = format_user_stats(stats)
    
    # Проверяем достижения
    achievement_service = AchievementService(session)
    new_achievements = await achievement_service.check_achievements(user.id)
    
    # Отправляем статистику
    await message.answer(stats_text, parse_mode="HTML", reply_markup=get_main_keyboard())
    
    # Если получены новые достижения, уведомляем пользователя
    if new_achievements:
        achievements_text = "\n\n".join([f"🌟 <b>{a.name}</b>\n<i>{a.description}</i>" for a in new_achievements])
        total_xp = sum(a.xp_reward for a in new_achievements)
        
        await message.answer(
            f"🎊 <b>Поздравляем! Новые достижения разблокированы!</b>\n\n{achievements_text}\n\n"
            f"🏅 Бонусный опыт: <b>+{total_xp} XP</b>",
            parse_mode="HTML"
        )


@router.message(F.text == "📊 Статистика")
async def show_stats(message: Message, session: AsyncSession):
    """Обработчик кнопки 'Статистика'"""
    await cmd_stats(message, session) 