from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = "1234567890:AAH_placeholder_token_for_setup_xyz"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/esavdo"
    WEBHOOK_URL: str = ""
    WEBHOOK_PATH: str = "/telegram-webhook"
    # Asosiy admin Telegram ID — .env da o'zgartiriladi, ilovani restart qilganda bazaga sinxronlanadi
    ADMIN_TELEGRAM_ID: int = 0
    ADMIN_GROUP_ID: int | None = None
    PRODUCT_ANNOUNCE_GROUP_ID: int | None = None
    RENDER_EXTERNAL_URL: str = ""

    # Do'kon brending sozlamalari (faqat shu yerda o'zgartiriladi va butun loyihaga ta'sir qiladi)
    STORE_NAME: str = "Online Savdo"
    STORE_DESCRIPTION: str = "Sifatli va qulay xaridlar platformasi"
    STORE_CURRENCY: str = "so'm"
    STORE_CONTACT_PHONE: str = ""
    STORE_LOGO_FILE_ID: str = ""
    TELEGRAM_APP_SHORT_NAME: str = "app"

    DEBUG: bool = False
    SELF_PING_INTERVAL_SECONDS: int = 300

    @field_validator("ADMIN_GROUP_ID", "PRODUCT_ANNOUNCE_GROUP_ID", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        if v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_base_url(self) -> str:
        if self.RENDER_EXTERNAL_URL and self.RENDER_EXTERNAL_URL.strip():
            return self.RENDER_EXTERNAL_URL.strip().rstrip("/")
        if self.WEBHOOK_URL and self.WEBHOOK_URL.strip():
            url = self.WEBHOOK_URL.strip()
            return url.replace(self.WEBHOOK_PATH, "").rstrip("/")
        return ""

    @property
    def effective_webhook_url(self) -> str:
        if self.WEBHOOK_URL and self.WEBHOOK_URL.strip():
            url = self.WEBHOOK_URL.strip()
            if not url.endswith(self.WEBHOOK_PATH):
                url = f"{url.rstrip('/')}{self.WEBHOOK_PATH}"
            return url
        if self.RENDER_EXTERNAL_URL and self.RENDER_EXTERNAL_URL.strip():
            base = self.RENDER_EXTERNAL_URL.strip().rstrip("/")
            return f"{base}{self.WEBHOOK_PATH}"
        return ""

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL.strip()
        # Handle postgres:// and postgresql:// -> postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # asyncpg does not support sslmode parameter in query string directly in some versions,
        # it prefers ssl=require or passing connect_args. But sqlalchemy handles it if formatted cleanly.
        return url


settings = Settings()
