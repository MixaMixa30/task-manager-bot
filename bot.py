import asyncio
import logging
import os
from datetime import time
import threading
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import load_config
from database.db import Database
from handlers import routers
from middlewares import DatabaseMiddleware
from services.achievement_service import AchievementService
from services.user_service import UserService
from services.task_service import TaskService
from utils.helpers import format_task_message # Добавляем импорт для форматирования

# Инициализация логгера
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
    # Загрузка конфигурации
    config = load_config()
    
    # Инициализация базы данных
    db = Database(config.db)
    
    # Инициализация хранилища состояний
    storage = MemoryStorage()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware
    dp.update.middleware(DatabaseMiddleware(db))
    
    # Регистрация всех маршрутизаторов
    for router in routers:
        dp.include_router(router)
    
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
    
    # Запуск веб-сервера для работы с Render
    port = int(os.environ.get("PORT", 10000))  # Render установит переменную PORT
    
    async def handle(request):
        return web.Response(text="TaskHero bot is running!")

    # Создаем простое веб-приложение
    app = web.Application()
    app.router.add_get('/', handle)
    
    # Функция для запуска веб-сервера в отдельном потоке
    def run_web_server():
        web.run_app(app, host='0.0.0.0', port=port)
    
    # Запускаем веб-сервер в отдельном потоке
    threading.Thread(target=run_web_server, daemon=True).start()
    logger.info(f"Веб-сервер запущен на порту {port}")
    
    # Запускаем бота в режиме поллинга
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}", exc_info=True) 