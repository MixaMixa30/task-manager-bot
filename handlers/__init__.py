# Инициализация пакета handlers 
import logging # Добавляем импорт для логирования

from handlers.common import router as common_router
from handlers.tasks import router as tasks_router
from handlers.achievements import router as achievements_router
from handlers.categories import router as categories_router

from aiogram import Dispatcher

# Список всех маршрутизаторов для подключения в основном файле
routers = [
    common_router,
    tasks_router,
    achievements_router,
    categories_router
]

logger = logging.getLogger(__name__) # Получаем логгер

def register_all_handlers(dp: Dispatcher):
    """Регистрирует все обработчики"""
    logger.info("Начало регистрации хендлеров...")
    for router in routers:
        dp.include_router(router)
        logger.info(f"Роутер {router.name} зарегистрирован.") # Логируем имя роутера
    logger.info("Регистрация хендлеров завершена.") 