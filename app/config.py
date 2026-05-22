from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str

    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    OPENAI_API_KEY: str = ""

    META_PHONE_NUMBER_ID: str
    META_ACCESS_TOKEN: str
    META_WEBHOOK_VERIFY_TOKEN: str
    META_APP_SECRET: str

    ADMIN_API_KEY: str

    KIWIFY_WEBHOOK_TOKEN: str = ""

    HOTMART_WEBHOOK_SECRET: str = ""
    HOTMART_OFFER_ID_TRIMESTRAL: str = ""
    HOTMART_OFFER_ID_ANUAL: str = ""

    PAYMENT_LINK_TRIMESTRAL: str = ""
    PAYMENT_LINK_ANUAL: str = ""

    ALLOWED_ORIGINS: str = "https://evolutionfit-api.onrender.com"


settings = Settings()
