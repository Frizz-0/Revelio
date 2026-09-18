from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    searxng_url: str

    revelio_env: str = "development"
    llm_cache_enabled: bool = True

    class Config:
        env_file = ".env"


settings = Settings()