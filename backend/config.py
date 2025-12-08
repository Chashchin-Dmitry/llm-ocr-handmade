from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "mysql+pymysql://ocr_user:ocr_pass@localhost:3306/ocr_documents"

    # vLLM Endpoints
    vllm_ocr_url: str = "http://localhost:8001"
    vllm_qwen_url: str = "http://localhost:8002"

    # File Upload
    upload_dir: str = "uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: set = {"png", "jpg", "jpeg", "pdf", "doc", "docx"}

    # Processing
    ocr_timeout: int = 120  # seconds
    structurizer_timeout: int = 60  # seconds

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
