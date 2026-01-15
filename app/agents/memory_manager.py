from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import AgentState, Message, Conversation
from app.schemas import MessageResponse


class MemoryManager:
    """记忆管理器"""

    def __init__(self, db: Session, agent_id: int, user_id: int):
        self.db = db
        self.agent_id = agent_id
        self.user_id = user_id

    def get_or_create_agent_state(self) -> AgentState:
        """获取或创建智能体状态"""
        agent_state = self.db.query(AgentState).filter(
            AgentState.user_id == self.user_id,
            AgentState.agent_id == self.agent_id
        ).first()

        if not agent_state:
            agent_state = AgentState(
                user_id=self.user_id,
                agent_id=self.agent_id,
                current_stage="陌生期",
                key_memories=[],
                user_traits={},
                conversation_topics=[]
            )
            self.db.add(agent_state)
            self.db.commit()
            self.db.refresh(agent_state)

        return agent_state

    def update_agent_state(
            self,
            user_input: str,
            agent_response: str,
            extracted_info: Dict[str, Any],
            conversation_id: int
    ) -> AgentState:
        """更新智能体状态"""
        agent_state = self.get_or_create_agent_state()

        # 移除total_messages字段引用
        agent_state.last_interaction_at = datetime.utcnow()
        agent_state.updated_at = datetime.utcnow()

        # 提取并添加关键记忆
        new_memories = self._extract_key_memories(user_input, agent_response, extracted_info)
        if new_memories:
            current_memories = agent_state.key_memories or []
            current_memories.extend(new_memories)

            # 保持记忆数量限制（最多15条）
            if len(current_memories) > 15:
                current_memories = current_memories[-15:]

            agent_state.key_memories = current_memories

            # 更新用户特征
        self._update_user_traits(agent_state, user_input, extracted_info)

        # 更新话题
        self._update_conversation_topics(agent_state, extracted_info)

        # 更新关系阶段
        self._update_relationship_stage(agent_state)

        self.db.commit()
        return agent_state

    def _extract_key_memories(
            self,
            user_input: str,
            agent_response: str,
            extracted_info: Dict[str, Any]
    ) -> List[str]:
        """提取关键记忆"""
        memories = []

        # 基于情感的强烈表达
        strong_emotions = ["愤怒", "悲伤", "喜悦", "恐惧"]
        for emotion in extracted_info.get("emotions", []):
            if emotion in strong_emotions:
                memory = f"对话中表达了强烈的{emotion}情绪"
                memories.append(memory)
                break

        # 重要关键词触发
        important_keywords = ["永远", "承诺", "誓言", "秘密", "真相", "对不起", "谢谢"]
        for keyword in important_keywords:
            if keyword in user_input or keyword in agent_response:
                # 提取包含关键词的句子
                import re
                text = user_input + " " + agent_response
                sentences = re.split(r'[。！？.!?]', text)
                for sentence in sentences:
                    if keyword in sentence and len(sentence.strip()) > 5:
                        memory = f"提到：{sentence.strip()[:50]}..."
                        memories.append(memory)
                        break
                break

        # 限制记忆长度
        return [mem[:100] for mem in memories[:2]]  # 最多2条，每条不超过100字

    def _update_user_traits(
            self,
            agent_state: AgentState,
            user_input: str,
            extracted_info: Dict[str, Any]
    ):
        """更新用户特征"""
        traits = agent_state.user_traits or {}

        # 初始化计数器
        if "interaction_count" not in traits:
            traits["interaction_count"] = 0
        traits["interaction_count"] += 1

        # 更新最后互动时间
        traits["last_interaction"] = datetime.utcnow().isoformat()

        # 基于话题推断兴趣
        topics = extracted_info.get("topics", [])
        if "interests" not in traits:
            traits["interests"] = []

        for topic in topics:
            if topic not in traits["interests"]:
                traits["interests"].append(topic)

        # 基于情感推断性格
        emotions = extracted_info.get("emotions", [])
        if "personality_traits" not in traits:
            traits["personality_traits"] = []

        emotion_to_trait = {
            "愤怒": "直接",
            "悲伤": "感性",
            "喜悦": "乐观",
            "矛盾": "谨慎"
        }

        for emotion in emotions:
            trait = emotion_to_trait.get(emotion)
            if trait and trait not in traits["personality_traits"]:
                traits["personality_traits"].append(trait)

        agent_state.user_traits = traits

    def _update_conversation_topics(
            self,
            agent_state: AgentState,
            extracted_info: Dict[str, Any]
    ):
        """更新对话话题"""
        topics = agent_state.conversation_topics or []
        new_topics = extracted_info.get("topics", [])

        for topic in new_topics:
            if topic not in topics:
                topics.append(topic)

        # 保持话题数量限制
        if len(topics) > 10:
            topics = topics[-10:]

        agent_state.conversation_topics = topics

    def _update_relationship_stage(self, agent_state: AgentState):
        """更新关系阶段"""
        # 动态计算互动次数
        interaction_count = self.db.query(Message).join(Conversation).filter(
            Conversation.user_id == self.user_id,
            Conversation.agent_id == self.agent_id
        ).count()

        # 基于互动次数调整阶段
        if interaction_count < 5:
            new_stage = "陌生期"
        elif interaction_count < 15:
            new_stage = "熟悉期"
        elif interaction_count < 30:
            new_stage = "友好期"
        else:
            new_stage = "亲密期"

            # 基于关键记忆数量调整
        key_memories_count = len(agent_state.key_memories or [])
        if key_memories_count > 8 and new_stage == "友好期":
            new_stage = "亲密期"

        if agent_state.current_stage != new_stage:
            agent_state.current_stage = new_stage

    def get_conversation_history(
            self,
            conversation_id: int,
            limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取对话历史"""
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(limit).all()

        # 转换为列表格式（从旧到新）
        history = []
        for msg in reversed(messages):
            history.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            })

        return history