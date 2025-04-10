from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    """Конфигурация для базы данных"""
    sqlite_db: str

    def get_url(self) -> str:
        """Получение URL для подключения к БД"""
        return f"sqlite+aiosqlite:///{self.sqlite_db}"


@dataclass
class TgBot:
    """Конфигурация для Telegram бота"""
    token: str


@dataclass
class Config:
    """Общая конфигурация приложения"""
    tg_bot: TgBot
    db: DatabaseConfig


def load_config() -> Config:
    """Загрузка конфигурации"""
    load_dotenv()

    return Config(
        tg_bot=TgBot(
            token=getenv('BOT_TOKEN', '8112151040:AAF1gH8ThZLoLC7zuTvUjAXgCqW3gQtmrEI'),
        ),
        db=DatabaseConfig(
            sqlite_db=getenv('SQLITE_DB', 'taskhero.db'),
        )
    ) 