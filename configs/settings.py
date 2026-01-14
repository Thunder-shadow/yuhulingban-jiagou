# configs/settings.py
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, PostgresDsn, validator


class Settings(BaseSettings):
    # 项目基础
    PROJECT_NAME: str = "多智能体对话系统"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # 服务器
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # 数据库
    DATABASE_URL: PostgresDsn = "postgresql://user:password@localhost/agent_system"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # LLM API
    LLM_API_BASE_URL: str = "https://api.deepseek.com"
    LLM_API_KEY: str = ""
    DEFAULT_MODEL: str = "DeepSeek-V3.1-Terminus"

    # 文件存储
    UPLOAD_DIR: Path = Path("uploads")
    MAX_UPLOAD_SIZE: int = 16 * 1024 * 1024  # 16MB

    # 速率限制
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()