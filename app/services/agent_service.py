# app/services/agent_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.models import AgentConfig, User
from app.schemas import AgentConfigCreate


class AgentService:
    """智能体服务"""

    def __init__(self, db: Session):
        self.db = db

    def list_agents(
            self,
            skip: int = 0,
            limit: int = 50,
            is_public: Optional[bool] = None,
            search: Optional[str] = None,
            category: Optional[str] = None
    ) -> List[AgentConfig]:
        """获取智能体列表"""
        query = self.db.query(AgentConfig)

        # 过滤条件
        if is_public is not None:
            query = query.filter(AgentConfig.is_public == is_public)

        if search:
            query = query.filter(
                or_(
                    AgentConfig.name.ilike(f"%{search}%"),
                    AgentConfig.display_name.ilike(f"%{search}%"),
                    AgentConfig.description.ilike(f"%{search}%")
                )
            )

        if category:
            # 假设character_profile中有category字段
            query = query.filter(AgentConfig.character_profile['category'].astext == category)

        # 排序和分页
        query = query.order_by(desc(AgentConfig.usage_count), desc(AgentConfig.created_at))
        query = query.offset(skip).limit(limit)

        return query.all()

    def get_agent(self, agent_id: int) -> Optional[AgentConfig]:
        """获取智能体"""
        return self.db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()

    def get_agent_by_name(self, agent_name: str) -> Optional[AgentConfig]:
        """通过名称获取智能体"""
        return self.db.query(AgentConfig).filter(AgentConfig.name == agent_name).first()

    def create_agent(self, agent_data: AgentConfigCreate, creator_id: int) -> AgentConfig:
        """创建智能体"""
        # 检查名称是否已存在
        existing = self.db.query(AgentConfig).filter(
            AgentConfig.name == agent_data.name
        ).first()

        if existing:
            raise ValueError(f"智能体名称 '{agent_data.name}' 已存在")

        # 创建智能体
        agent = AgentConfig(
            name=agent_data.name,
            display_name=agent_data.display_name,
            character_profile=agent_data.character_profile,
            opening_statement=agent_data.opening_statement,
            background_story=agent_data.background_story,
            #creator_id=creator_id,
            is_active=1,  # 修改：使用整数1
            #is_public=False,  # 保持不变
            created_at=datetime.utcnow(),
            #updated_at=datetime.utcnow()
        )

        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)

        return agent

    def update_agent(self, agent_id: int, agent_data: AgentConfigCreate) -> AgentConfig:
        """更新智能体"""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError("智能体不存在")

        # 更新字段
        agent.display_name = agent_data.display_name
        agent.description = agent_data.description
        agent.character_profile = agent_data.character_profile
        agent.opening_statement = agent_data.opening_statement
        agent.background_story = agent_data.background_story
        agent.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(agent)

        return agent

    def delete_agent(self, agent_id: int) -> bool:
        """删除智能体"""
        agent = self.get_agent(agent_id)
        if not agent:
            return False

        # 检查是否有对话关联
        from app.models import Conversation
        conversation_count = self.db.query(Conversation).filter(
            Conversation.agent_id == agent_id
        ).count()

        if conversation_count > 0:
            raise ValueError("无法删除，该智能体已有对话记录")

        self.db.delete(agent)
        self.db.commit()

        return True

    def update_agent_usage(self, agent_id: int):
        """更新智能体使用统计"""
        agent = self.get_agent(agent_id)
        if not agent:
            return

        agent.usage_count += 1
        agent.updated_at = datetime.utcnow()
        self.db.commit()

    def set_agent_visibility(self, agent_id: int, is_public: bool) -> AgentConfig:
        """设置智能体可见性"""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError("智能体不存在")

        agent.is_public = is_public
        agent.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(agent)

        return agent

    def get_user_agents(self, user_id: int, is_public: Optional[bool] = None) -> List[AgentConfig]:
        """获取用户创建或有权访问的智能体"""
        query = self.db.query(AgentConfig).filter(
            AgentConfig.creator_id == user_id
        )

        if is_public is not None:
            query = query.filter(AgentConfig.is_public == is_public)

        return query.order_by(desc(AgentConfig.created_at)).all()

    def import_agent_from_config(self, config_dict: Dict[str, Any], creator_id: int) -> AgentConfig:
        """从配置文件导入智能体"""
        # 验证必需字段
        required_fields = ['name', 'display_name', 'character_profile']
        for field in required_fields:
            if field not in config_dict:
                raise ValueError(f"缺少必需字段: {field}")

        # 检查名称是否已存在
        existing = self.db.query(AgentConfig).filter(
            AgentConfig.name == config_dict['name']
        ).first()

        if existing:
            # 如果存在，添加后缀
            import uuid
            config_dict['name'] = f"{config_dict['name']}_{str(uuid.uuid4())[:8]}"

        # 创建智能体
        agent = AgentConfig(
            name=config_dict['name'],
            display_name=config_dict['display_name'],
            description=config_dict.get('description'),
            character_profile=config_dict['character_profile'],
            opening_statement=config_dict.get('opening_statement'),
            background_story=config_dict.get('background_story'),
            model_config=config_dict.get('model_config', {
                "provider": "openai_api_compatible",
                "model": "Pro/deepseek-ai/DeepSeek-V3",
                "temperature": 0.8
            }),
            stages=config_dict.get('stages', ["陌生期", "熟悉期", "友好期", "亲密期"]),
            output_format=config_dict.get('output_format', {
                "max_length": 150,
                "format_rules": "旁白无需括号，每条旁白与独白必须换行"
            }),
            icon=config_dict.get('icon', '🤖'),
            icon_background=config_dict.get('icon_background', '#FFEAD5'),
            creator_id=creator_id,
            is_active=True,
            is_public=config_dict.get('is_public', False)
        )

        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)

        return agent