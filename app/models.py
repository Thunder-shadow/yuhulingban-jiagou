# models.py
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    conversations = relationship("Conversation", back_populates="user")
    agent_states = relationship("AgentState", back_populates="user")


class AgentConfig(Base):
    """智能体配置表"""
    __tablename__ = 'agent_configs'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    display_name = Column(String(100))
    icon = Column(String(50))
    icon_background = Column(String(20))

    # 角色设定（JSON格式存储）
    character_profile = Column(JSON)  # 存储完整的角色设定JSON
    opening_statement = Column(Text)  # 开场白
    background_story = Column(Text)  # 背景故事

    # 模型配置
    model_config = Column(JSON, default={
        "provider": "openai_api_compatible",
        "model": "DeepSeek-V3.1-Terminus",
        "temperature": 1.0,
        "top_p": 0.4,
        "presence_penalty": 0.2
    })

    # 阶段定义
    stages = Column(JSON, default=["陌生期", "熟悉期", "友好期", "亲密期"])

    # 输出格式要求
    output_format = Column(JSON, default={
        "max_length": 150,
        "format_rules": "旁白无需括号，每条旁白与独白必须换行"
    })

    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    conversations = relationship("Conversation", back_populates="agent")
    agent_states = relationship("AgentState", back_populates="agent")


class Conversation(Base):
    """对话会话表"""
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    agent_id = Column(Integer, ForeignKey('agent_configs.id'))
    title = Column(String(255))  # 对话标题（自动生成）

    # 当前状态
    current_stage = Column(String(50), default="陌生期")
    metadata = Column(JSON, default={})  # 额外的元数据

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="conversations")
    agent = relationship("AgentConfig", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                            order_by="Message.created_at")


class Message(Base):
    """消息表"""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'))

    # 消息内容
    role = Column(String(20))  # 'user' 或 'assistant'
    content = Column(Text)
    formatted_content = Column(Text)  # 格式化后的内容

    # 元数据
    token_count = Column(Integer)
    model_used = Column(String(100))
    metadata = Column(JSON, default={})  # 如：情感分析、主题等

    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")


class AgentState(Base):
    """用户与智能体的状态表（记忆核心）"""
    __tablename__ = 'agent_states'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    agent_id = Column(Integer, ForeignKey('agent_configs.id'))

    # 记忆系统
    memory_embeddings = Column(JSON)  # 向量记忆（可选）
    key_memories = Column(JSON, default=[])  # 关键记忆点
    relationship_level = Column(Integer, default=0)  # 关系等级 0-100
    current_stage = Column(String(50), default="陌生期")

    # 统计信息
    total_messages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # 偏好和特征
    user_traits = Column(JSON, default={})  # 从对话中提取的用户特征
    conversation_topics = Column(JSON, default=[])  # 讨论过的话题

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="agent_states")
    agent = relationship("AgentConfig", back_populates="agent_states")


# 数据库连接
DATABASE_URL = "postgresql://user:password@localhost/agent_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()