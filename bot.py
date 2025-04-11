import asyncio
import logging
import os
import sys
from datetime import time

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import load_config
from database.db import Database
from database.models import Base
from middlewares import register_all_middlewares
from handlers import register_all_handlers
from services.achievement_service import AchievementService
from services.user_service import UserService
from services.task_service import TaskService
from utils.helpers import format_task_message # Добавляем импорт для форматирования

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Регистрация команд бота
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Получить помощь"),
        BotCommand(command="tasks", description="Управление задачами"),
        BotCommand(command="achievements", description="Мои достижения"),
        BotCommand(command="stats", description="Моя статистика"),
    ]
    await bot.set_my_commands(commands)

# Функция для отправки ежедневных напоминаний
async def send_daily_reminders(bot: Bot, db: Database):
    logger.info("Запуск отправки ежедневных напоминаний...")
    async for session in db.get_session():
        user_service = UserService(session)
        task_service = TaskService(session)
        users = await user_service.get_all_users()
        
        for user in users:
            tasks_today = await task_service.get_tasks_due_today(user.id)
            if tasks_today:
                reminder_text = "⏰ <b>Напоминание о квестах на сегодня:</b>\n\n"
                for task in tasks_today:
                    # Используем существующий хелпер для форматирования
                    reminder_text += f"• {task.title}\n"
                    # Можно добавить более детальный формат, если нужно
                    # reminder_text += format_task_message(task) + "\n\n"
                
                try:
                    await bot.send_message(user.tg_id, reminder_text, parse_mode="HTML")
                    logger.info(f"Отправлено напоминание пользователю {user.tg_id}")
                except Exception as e:
                    logger.error(f"Ошибка отправки напоминания пользователю {user.tg_id}: {e}")
            # else:
            #     logger.info(f"У пользователя {user.tg_id} нет задач на сегодня.")
    logger.info("Отправка ежедневных напоминаний завершена.")

# Функция для настройки и запуска бота
async def main():
    # Проверка на уже запущенный экземпляр
    pid_file = 'bot.pid'
    if os.path.isfile(pid_file):
        try:
            with open(pid_file) as f:
                old_pid = int(f.read())
            # Проверяем, существует ли процесс с таким PID
            os.kill(old_pid, 0)
            logger.error(f"Бот уже запущен с PID {old_pid}")
            sys.exit(1)
        except (ProcessLookupError, ValueError):
            # Если процесс не существует или PID некорректный, удаляем файл
            os.remove(pid_file)
    
    # Записываем PID текущего процесса
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    
    # Загрузка конфигурации
    config = load_config()
    
    # Инициализация базы данных
    db = Database(config.db)
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.tg_bot.token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация middleware
    register_all_middlewares(dp, db)
    
    # Регистрация хендлеров
    register_all_handlers(dp)
    
    # Создание таблиц БД
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Регистрация команд бота
    await set_commands(bot)
    
    # Создание стандартных достижений при первом запуске (можно оптимизировать)
    try:
        async for session in db.get_session():
            achievement_service = AchievementService(session)
            await achievement_service.create_default_achievements()
    except Exception as e:
        logger.error(f"Ошибка создания стандартных достижений: {e}")

    # Инициализация и запуск планировщика
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow") # Укажи свою таймзону
    # Добавляем задачу на ежедневную отправку напоминаний в 9:00
    scheduler.add_job(
        send_daily_reminders,
        trigger=CronTrigger(hour=9, minute=0),
        kwargs={'bot': bot, 'db': db}
    )
    scheduler.start()
    logger.info("Планировщик запущен.")
    
    # Пропуск обновлений и запуск поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    finally:
        # Удаляем PID файл при завершении
        if os.path.exists('bot.pid'):
            os.remove('bot.pid') 