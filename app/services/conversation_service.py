# app/services/conversation_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Conversation, Message, AgentConfig, User
from app.schemas import ConversationCreate, MessageCreate


class ConversationService:
    """对话服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_conversation(
            self,
            user_id: int,
            agent_id: int,
            title: Optional[str] = None
    ) -> Conversation:
        """创建对话"""
        # 检查智能体是否存在
        agent = self.db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
        if not agent:
            raise ValueError("智能体不存在")

        # 创建对话
        conversation = Conversation(
            user_id=user_id,
            agent_id=agent_id,
            title=title or f"与{agent.display_name}的对话",
            current_stage="陌生期"
        )

        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        # 更新用户对话计数
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.conversation_count += 1
            self.db.commit()

        return conversation

    def get_conversation(self, conversation_id: int, user_id: Optional[int] = None) -> Optional[Conversation]:
        """获取对话"""
        query = self.db.query(Conversation).filter(Conversation.id == conversation_id)

        if user_id:
            query = query.filter(Conversation.user_id == user_id)

        return query.first()

    def get_user_conversations(
            self,
            user_id: int,
            skip: int = 0,
            limit: int = 50
    ) -> List[Conversation]:
        """获取用户的对话列表"""
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_conversation_title(self, conversation_id: int, title: str) -> Conversation:
        """更新对话标题"""
        conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise ValueError("对话不存在")

        conversation.title = title
        conversation.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(conversation)

        return conversation

    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """删除对话"""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()

        if not conversation:
            return False

        # 删除相关消息
        self.db.query(Message).filter(Message.conversation_id == conversation_id).delete()

        # 删除对话
        self.db.delete(conversation)
        self.db.commit()

        return True

    def add_message(
            self,
            conversation_id: int,
            message_data: MessageCreate,
            token_count: int = 0,
            model_used: Optional[str] = None
    ) -> Message:
        """添加消息"""
        # 检查对话是否存在
        conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise ValueError("对话不存在")

        # 创建消息
        message = Message(
            conversation_id=conversation_id,
            role=message_data.role,
            content=message_data.content,
            formatted_content=message_data.content,
            token_count=token_count,
            model_used=model_used
        )

        self.db.add(message)

        # 更新对话统计
        conversation.message_count += 1
        conversation.total_tokens += token_count
        conversation.updated_at = datetime.utcnow()
        conversation.last_message_at = datetime.utcnow()

        # 更新用户统计
        user = self.db.query(User).filter(User.id == conversation.user_id).first()
        if user:
            user.message_count += 1
            user.total_tokens_used += token_count

        self.db.commit()
        self.db.refresh(message)

        return message

    def get_conversation_messages(
            self,
            conversation_id: int,
            user_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Message]:
        """获取对话消息"""
        query = self.db.query(Message).filter(Message.conversation_id == conversation_id)

        if user_id:
            # 检查对话是否属于用户
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            ).first()
            if not conversation:
                return []

        return (
            query
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )