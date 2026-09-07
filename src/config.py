import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация Color Bot."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = "YOUR_BOT_TOKEN_HERE"
    bot_username: Optional[str] = None
    cache_dir: str = "/tmp/color_bot_cache"
    default_font_path: str = "assets/fonts/Comfortaa-Bold.ttf"
    max_tgs_size: int = 63 * 1024  # 63 KB Telegram limit
    session_ttl_seconds: int = 1800


settings = Settings()
os.makedirs(settings.cache_dir, exist_ok=True)
