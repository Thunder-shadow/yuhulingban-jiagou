# app/utils/cache.py
import functools
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional
from sqlalchemy.orm import Session
from configs.settings import settings
import redis

# Redis连接
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def cache_query(expire_minutes: int = 5):
    """SQL查询缓存装饰器"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(db: Session, *args, **kwargs):
            # 生成缓存键
            cache_key = f"query:{func.__name__}:{_generate_cache_key(args, kwargs)}"

            # 尝试从Redis获取缓存
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)

                # 执行查询
            result = func(db, *args, **kwargs)

            # 缓存结果
            redis_client.setex(
                cache_key,
                expire_minutes * 60,
                json.dumps(result, default=str)
            )

            return result

        return wrapper

    return decorator


def _generate_cache_key(args, kwargs) -> str:
    """生成缓存键"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()