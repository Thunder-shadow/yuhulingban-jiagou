# app/agents/agent_factory.py
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import AgentConfig
from app.agents.character_agent import CharacterAgent
from configs.settings import settings


class AgentFactory:
    """智能体工厂"""

    def __init__(self, db: Session):
        self.db = db
        self._agents_cache = {}

    def get_agent(self, agent_id: int) -> Optional[CharacterAgent]:
        """获取智能体实例"""
        if agent_id in self._agents_cache:
            return self._agents_cache[agent_id]

        agent_config = self.db.query(AgentConfig).filter(AgentConfig.id == agent_id).first()
        if not agent_config:
            return None

        agent = CharacterAgent(agent_config, settings.LLM_API_BASE_URL, settings.LLM_API_KEY)
        self._agents_cache[agent_id] = agent
        return agent

    def get_agent_by_name(self, agent_name: str) -> Optional[CharacterAgent]:
        """通过名称获取智能体"""
        agent_config = self.db.query(AgentConfig).filter(AgentConfig.name == agent_name).first()
        if not agent_config:
            return None

        return self.get_agent(agent_config.id)

    def clear_cache(self, agent_id: Optional[int] = None):
        """清除缓存"""
        if agent_id:
            self._agents_cache.pop(agent_id, None)
        else:
            self._agents_cache.clear()