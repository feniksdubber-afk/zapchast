"""
Loyiha konfiguratsiyasi.
Barcha muhit o'zgaruvchilari (env) shu yerdan boshqariladi.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str

    # Aros Market API
    AROS_BASE_URL: str = "https://api.aros.uz/api/v1"
    AROS_PAGE_SIZE: int = 10  # Bir qidiruv natijasida nechta mahsulot

    # HTTP klient sozlamalari
    HTTP_TIMEOUT: float = 10.0       # Soniyalarda: javob kutish vaqti
    HTTP_MAX_RETRIES: int = 2        # Muvaffaqiyatsiz so'rovni necha marta qayta urinish

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


# Loyiha bo'ylab yagona settings obyekti
settings = Settings()
