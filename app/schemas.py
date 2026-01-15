# app/schemas.py
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class Token(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """令牌数据"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None


class UserBase(BaseModel):
    """用户基础模型"""
    username: str
    email: EmailStr
    display_name: Optional[str] = None


class UserCreate(UserBase):
    """用户创建模型"""
    password: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        return v


class UserLogin(BaseModel):
    """用户登录模型"""
    identifier: str  # 用户名或邮箱
    password: str


class UserUpdate(BaseModel):
    """用户更新模型"""
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None


class UserInDB(UserBase):
    """数据库用户模型"""
    id: int
    status: str
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentConfigBase(BaseModel):
    """智能体配置基础模型"""
    name: str
    display_name: str
    description: Optional[str] = None
    character_profile: Dict[str, Any]


class AgentConfigCreate(AgentConfigBase):
    """智能体创建模型"""
    opening_statement: Optional[str] = None
    background_story: Optional[str] = None


class AgentConfigResponse(AgentConfigBase):
    """智能体响应模型"""
    id: int
    icon: str
    icon_background: str
    is_public: bool
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    """消息基础模型"""
    content: str
    role: str


class MessageCreate(MessageBase):
    """消息创建模型"""
    pass


class MessageResponse(MessageBase):
    """消息响应模型"""
    id: int
    conversation_id: int
    created_at: datetime
    token_count: Optional[int] = None

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """对话基础模型"""
    agent_id: int
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    """对话创建模型"""
    pass


class ConversationResponse(ConversationBase):
    """对话响应模型"""
    id: int
    user_id: int
    current_stage: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    conversation_id: Optional[int] = None
    user_info: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    conversation_id: int
    agent_name: str
    current_stage: str
    message_id: int
    timestamp: datetime


class ChangePasswordRequest(BaseModel):
    """修改密码请求模型"""
    old_password: str
    new_password: str

    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('新密码长度至少8位')
        return v