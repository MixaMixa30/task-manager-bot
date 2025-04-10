# Инициализация пакета handlers 
from handlers.common import router as common_router
from handlers.tasks import router as tasks_router
from handlers.achievements import router as achievements_router
from handlers.categories import router as categories_router

# Список всех маршрутизаторов для подключения в основном файле
routers = [
    common_router,
    tasks_router,
    achievements_router,
    categories_router
] 