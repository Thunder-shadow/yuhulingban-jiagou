# app/api/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    UserCreate, UserLogin, UserUpdate, UserInDB,
    Token, ChangePasswordRequest
)
from app.services.user_service import UserService
from app.security import security_manager

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
        user_data: UserCreate,
        db: Session = Depends(get_db)
):
    """用户注册"""
    service = UserService(db)

    try:
        user = service.create_user(user_data)

        # 创建访问令牌
        access_token = security_manager.create_access_token(
            data={"sub": user.username, "user_id": user.id, "role": user.role.value}
        )

        return {
            "message": "注册成功",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=dict)
async def login(
        login_data: UserLogin,
        db: Session = Depends(get_db)
):
    """用户登录"""
    service = UserService(db)

    user = service.authenticate_user(login_data.identifier, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建访问令牌
    access_token = security_manager.create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role.value}
    )

    # 创建刷新令牌
    refresh_token = security_manager.create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "avatar_url": user.avatar_url,
            "preferences": user.preferences
        }
    }


@router.get("/me", response_model=dict)
async def get_current_user_info(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """获取当前用户信息"""
    service = UserService(db)

    # 动态计算统计数据
    from app.models import Conversation, Message
    conversation_count = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).count()

    message_count = db.query(Message).join(Conversation).filter(
        Conversation.user_id == current_user.id
    ).count()

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "avatar_url": current_user.avatar_url,
        "bio": current_user.bio,
        "gender": current_user.gender,
        "role": current_user.role.value,
        "status": current_user.status.value,
        "preferences": current_user.preferences,
        "stats": {
            "message_count": message_count,  # 动态计算
            "conversation_count": conversation_count,  # 动态计算
            "login_count": current_user.login_count
        },
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat()
    }


@router.put("/me", response_model=dict)
async def update_user_info(
        update_data: UserUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """更新用户信息"""
    service = UserService(db)

    try:
        user = service.update_user(current_user.id, update_data)
        return {
            "message": "更新成功",
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "bio": user.bio,
                "gender": user.gender,
                "location": user.location
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/change-password", response_model=dict)
async def change_password(
        password_data: ChangePasswordRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """修改密码"""
    service = UserService(db)

    success = service.change_password(
        current_user.id,
        password_data.old_password,
        password_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )

    return {"message": "密码修改成功"}


@router.post("/refresh-token", response_model=dict)
async def refresh_token(
        refresh_token: str,
        db: Session = Depends(get_db)
):
    """刷新访问令牌"""
    payload = security_manager.decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    # 查找用户
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    # 创建新的访问令牌
    access_token = security_manager.create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role.value}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }