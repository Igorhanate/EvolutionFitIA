from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str

    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    EVOLUTION_API_URL: str
    EVOLUTION_API_TOKEN: str
    EVOLUTION_API_INSTANCE: str

    ADMIN_API_KEY: str

    HOTMART_WEBHOOK_SECRET: str
    HOTMART_OFFER_ID_TRIMESTRAL: str
    HOTMART_OFFER_ID_ANUAL: str

    PAYMENT_LINK_TRIMESTRAL: str
    PAYMENT_LINK_ANUAL: str

    ALLOWED_ORIGINS: str = "https://evolutionfit-api.onrender.com"


settings = Settings()
