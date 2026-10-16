from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/one_request_many_actions.db"
    google_api_key: str | None = None
    google_model: str = "gemini-2.5-flash"
    agent_mode: str = "auto"
    mcp_server_url: str = "http://127.0.0.1:8001/mcp"
    mcp_transport: str = "streamable-http"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8001


@lru_cache
def get_settings() -> Settings:
    return Settings()
