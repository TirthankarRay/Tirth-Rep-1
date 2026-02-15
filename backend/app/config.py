from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sclc_user:sclc_dev_password@localhost:5432/sclc_dashboard"
    environment: str = "development"

    model_config = {"env_file": ".env"}


settings = Settings()
