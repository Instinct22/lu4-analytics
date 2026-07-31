from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://lu4:lu4secret@db:5432/lu4"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60 * 24
    jwt_refresh_expire_days: int = 7
    import_api_key: str = "change-import-key"
    cors_origins: str = "http://localhost,http://localhost:5173"
    wiki_path: str = "/data/wiki"
    datasets_path: str = "/data/datasets"

    seed_users: str = "admin:admin123,user1:pass123"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
