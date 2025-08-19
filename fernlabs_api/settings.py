from pydantic_settings import BaseSettings
from typing import Optional


class APISettings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = "postgresql://postgres:password@localhost/fernlabs"

    # OpenAI
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
