# app/services/chat_service.py
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import User, AgentConfig, Conversation, Message, AgentState
from app.agents.agent_factory import AgentFactory
from app.agents.memory_manager import MemoryManager
from app.schemas import MessageCreate
from app.services.conversation_service import ConversationService
from app.services.agent_service import AgentService

class ChatService:
    """聊天服务"""

    def __init__(self, db: Session):
        self.db = db
        self.agent_factory = AgentFactory(db)
        self.conversation_service = ConversationService(db)

    async def process_chat(
            self,
            user_id: int,
            agent_name: str,
            message: str,
            conversation_id: Optional[int] = None,
            user_info: Optional[Dict[str, Any]] = None,
            stream: bool = False
    ) -> Dict[str, Any]:
        """处理聊天消息（优化版）"""

        # 1. 获取或创建对话
        conversation = None
        if conversation_id:
            conversation = self.conversation_service.get_conversation(conversation_id, user_id)

            # 2. 获取智能体（使用缓存）
        agent_service = AgentService(self.db)
        agent_config_dict = agent_service.get_agent_by_name(agent_name)

        if not agent_config_dict:
            raise ValueError(f"智能体 '{agent_name}' 不存在")

        if not conversation:
            # 创建新对话
            conversation = self.conversation_service.create_conversation(
                user_id=user_id,
                agent_id=agent_config_dict["id"],
                title=f"与{agent_config_dict['display_name']}的对话"
            )

            # 3. 保存用户消息
        user_message = self.conversation_service.add_message(
            conversation_id=conversation.id,
            message_data=MessageCreate(content=message, role="user"),
            token_count=len(message) // 2
        )

        # 4. 获取智能体和记忆管理器
        agent = self.agent_factory.get_agent(agent_config_dict["id"])
        memory_manager = MemoryManager(self.db, agent_config_dict["id"], user_id)

        # 5. 获取对话历史和智能体状态
        history = memory_manager.get_conversation_history(conversation.id, limit=10)
        agent_state = memory_manager.get_or_create_agent_state()

        # 6. 构建用户信息
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user_info:
            user_info = {
                "name": user.username,
                "gender": user.gender or "unknown",
                "traits": user.bio or ""
            }

            # 7. 生成响应
        result = agent.generate_response(
            user_input=message,
            user_info=user_info,
            agent_state=agent_state,
            conversation_history=history
        )

        # 8. 批量保存所有更新（合并事务）
        try:
            # 保存AI响应
            ai_message = self.conversation_service.add_message(
                conversation_id=conversation.id,
                message_data=MessageCreate(content=result["response"], role="assistant"),
                token_count=len(result["raw_response"]) // 2,
                model_used=result["model_used"]
            )

            # 更新记忆
            memory_manager.update_agent_state(
                user_input=message,
                agent_response=result["raw_response"],
                extracted_info=result["extracted_info"],
                conversation_id=conversation.id
            )

            # 批量更新所有相关状态
            conversation.current_stage = agent_state.current_stage
            conversation.updated_at = datetime.utcnow()
            conversation.last_message_at = datetime.utcnow()

            # 更新智能体使用统计
            agent_config = self.db.query(AgentConfig).filter(
                AgentConfig.id == agent_config_dict["id"]
            ).first()
            agent_config.usage_count += 1

            # 统一提交所有更改
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise e

        return {
            "response": result["response"],
            "conversation_id": conversation.id,
            "agent_name": agent_config_dict["display_name"],
            "current_stage": agent_state.current_stage,
            "message_id": ai_message.id,
            "timestamp": result["timestamp"],
            "tokens_used": ai_message.token_count + user_message.token_count
        }

    def get_conversation_messages(
            self,
            conversation_id: int,
            user_id: Optional[int] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取对话消息"""
        messages = self.conversation_service.get_conversation_messages(
            conversation_id, user_id, skip, limit
        )

        result = []
        for msg in messages:
            result.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.formatted_content or msg.content,
                "timestamp": msg.created_at.isoformat(),
                "token_count": msg.token_count,
                "model_used": msg.model_used
            })

        return result

    async def continue_conversation(
            self,
            conversation_id: int,
            user_id: int,
            initial_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """继续已有对话"""
        conversation = self.conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise ValueError("对话不存在或无权访问")

            # 获取智能体
        agent_config = self.db.query(AgentConfig).filter(
            AgentConfig.id == conversation.agent_id
        ).first()

        if not agent_config:
            raise ValueError("关联的智能体不存在")

            # 获取最近的消息作为上下文
        recent_messages = self.get_conversation_messages(conversation_id, user_id, limit=3)

        # 如果没有初始消息，生成一个开场
        if not initial_message and not recent_messages:
            initial_message = "让我们继续之前的对话吧。"

        if initial_message:
            # 如果有初始消息，发送它
            return await self.process_chat(
                user_id=user_id,
                agent_name=agent_config.name,
                message=initial_message,
                conversation_id=conversation_id
            )
        else:
            # 否则返回对话信息
            return {
                "conversation_id": conversation.id,
                "agent_name": agent_config.display_name,
                "current_stage": conversation.current_stage,
                "message_count": len(recent_messages),
                "last_updated": conversation.updated_at.isoformat(),
                "recent_messages": recent_messages
            }