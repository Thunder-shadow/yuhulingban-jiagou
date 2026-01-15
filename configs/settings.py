# configs/settings.py
import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, EmailStr, field_validator


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
    DATABASE_URL: PostgresDsn = "postgresql://yuhulingban:yuhulingban@localhost:5432/yuhulingban"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天

    # LLM API
    LLM_API_BASE_URL: str = "https://api.siliconflow.cn/v1"
    LLM_API_KEY: str = "sk-mbptrzkhtqyrwzagbkapraweuelhdpyyxigmnahgkofwohlh"
    DEFAULT_MODEL: str = "DeepSeek-V3"

    # 文件存储
    UPLOAD_DIR: Path = Path("uploads")
    MAX_UPLOAD_SIZE: int = 16 * 1024 * 1024  # 16MB

    # 速率限制
    RATE_LIMIT_PER_MINUTE: int = 60

    # 缓存配置
    CACHE_TTL_SECONDS: int = 300  # 5分钟
    AGENT_CACHE_TTL: int = 600  # 10分钟
    USER_CACHE_TTL: int = 300  # 5分钟

    # 流式响应配置
    STREAM_CHUNK_SIZE: int = 100  # 流式响应块大小
    STREAM_TIMEOUT: int = 30  # 流式响应超时时间

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()