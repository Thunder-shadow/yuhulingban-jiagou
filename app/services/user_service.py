# app/services/user_service.py
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import User, UserStatus, UserRole, UserActivityLog
from app.schemas import UserCreate, UserUpdate
from app.security import security_manager
from app.utils.cache import redis_client
import json

class UserService:
    """用户服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_with_cache(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户信息（带Redis缓存）"""
        cache_key = f"user:{user_id}"

        # 尝试从Redis获取
        cached_user = redis_client.get(cache_key)
        if cached_user:
            return json.loads(cached_user)

            # 从数据库查询
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        user_data = {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "gender": user.gender,
            "role": user.role.value,
            "status": user.status.value,
            "preferences": user.preferences
        }

        # 缓存到Redis（5分钟）
        redis_client.setex(cache_key, 300, json.dumps(user_data))

        return user_data

    def invalidate_user_cache(self, user_id: int):
        """清除用户缓存"""
        cache_key = f"user:{user_id}"
        redis_client.delete(cache_key)

    def create_user(self, user_data: UserCreate, ip_address: Optional[str] = None) -> User:
        """创建用户"""
        # 检查用户名和邮箱是否已存在
        existing_user = self.db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()

        if existing_user:
            raise ValueError("用户名或邮箱已存在")

        # 创建用户
        user = User(
            username=user_data.username,
            email=user_data.email,
            display_name=user_data.display_name or user_data.username,
            hashed_password=security_manager.hash_password(user_data.password),
            salt="",  # passlib会自动处理salt
            status=UserStatus.ACTIVE,
            role=UserRole.USER,
            preferences={
                "language": "zh-CN",
                "theme": "light",
                "notification_enabled": True,
            }
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # 记录活动
        self.log_activity(user.id, "register", {"username": user_data.username}, ip_address)

        return user

    def authenticate_user(
            self,
            identifier: str,
            password: str,
            ip_address: Optional[str] = None
    ) -> Optional[User]:
        """用户认证"""
        # 查找用户
        user = self.db.query(User).filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if not user:
            return None

        # 检查账号状态
        if user.status != UserStatus.ACTIVE:
            return None

        # 验证密码
        if not security_manager.verify_password(password, user.hashed_password):
            return None

        # 更新登录信息
        user.last_login_at = datetime.utcnow()
        user.last_active_at = datetime.utcnow()
        user.login_count += 1
        self.db.commit()

        # 记录活动
        self.log_activity(user.id, "login", {"method": "password"}, ip_address)

        return user

    def update_user(self, user_id: int, update_data: UserUpdate) -> User:
        """更新用户"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        # 更新字段
        for field, value in update_data.dict(exclude_none=True).items():
            setattr(user, field, value)

        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)

        return user

    def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> User:
        """更新用户偏好"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        current_prefs = user.preferences or {}
        current_prefs.update(preferences)
        user.preferences = current_prefs
        user.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(user)

        return user

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # 验证旧密码
        if not security_manager.verify_password(old_password, user.hashed_password):
            return False

        # 更新密码
        user.hashed_password = security_manager.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        self.db.commit()

        # 记录活动
        self.log_activity(user_id, "change_password", {})

        return True

    def request_password_reset(self, email: str) -> bool:
        """请求密码重置"""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return False  # 安全考虑，不提示用户是否存在

        # 生成重置令牌
        user.password_reset_token = security_manager.generate_password_reset_token(user.id)
        user.password_reset_sent_at = datetime.utcnow()

        self.db.commit()

        # TODO: 发送重置邮件
        # send_password_reset_email(user.email, user.password_reset_token)

        return True

    def reset_password(self, token: str, new_password: str) -> bool:
        """重置密码"""
        payload = security_manager.decode_token(token)
        if not payload or payload.get("type") != "password_reset":
            return False

        user_id = payload.get("user_id")
        if not user_id:
            return False

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # 检查令牌是否匹配
        if user.password_reset_token != token:
            return False

        # 检查令牌是否过期（1小时）
        if (datetime.utcnow() - user.password_reset_sent_at).total_seconds() > 3600:
            return False

        # 更新密码
        user.hashed_password = security_manager.hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_sent_at = None
        user.updated_at = datetime.utcnow()

        self.db.commit()

        # 记录活动
        self.log_activity(user_id, "reset_password", {})

        return True

    def log_activity(
            self,
            user_id: int,
            action_type: str,
            details: Dict[str, Any],
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None
    ):
        """记录用户活动"""
        log = UserActivityLog(
            user_id=user_id,
            action_type=action_type,
            action_details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(log)
        self.db.commit()