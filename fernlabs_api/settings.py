from pydantic_settings import BaseSettings
from typing import Optional


class APISettings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = "postgresql://postgres:password@localhost/fernlabs"

    # AI Model Configuration
    api_model_type: str = "mistral"  # openai, gemini, mistral, anthropic
    api_model_provider: str = "mistral"  # Provider name for the factory function
    api_model_name: str = "mistral:mistral-large-latest"  # Full model identifier
    api_model_key: Optional[str] = None  # API key for the selected provider

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
