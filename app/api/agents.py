# app/api/agents.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_user, get_current_admin_user
from app.models import User, AgentConfig
from app.schemas import AgentConfigResponse, AgentConfigCreate
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=List[AgentConfigResponse])
async def list_agents(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        is_public: Optional[bool] = None,
        current_user: Optional[User] = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """获取智能体列表"""
    service = AgentService(db)

    # 普通用户只能看到公开的智能体
    if current_user and current_user.role not in ["admin", "super_admin"]:
        is_public = True

    return service.list_agents(skip=skip, limit=limit, is_public=is_public)


@router.get("/{agent_id}", response_model=AgentConfigResponse)
async def get_agent(
        agent_id: int,
        current_user: Optional[User] = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """获取智能体详情"""
    service = AgentService(db)

    agent = service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="智能体不存在"
        )

    # 检查权限
    if not agent.is_public and (
            not current_user or
            current_user.role not in ["admin", "super_admin"]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此智能体"
        )

    return agent


@router.post("/", response_model=AgentConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
        agent_data: AgentConfigCreate,
        current_user: User = Depends(get_current_admin_user),
        db: Session = Depends(get_db)
):
    """创建智能体（管理员）"""
    service = AgentService(db)

    try:
        agent = service.create_agent(agent_data, current_user.id)
        return agent
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{agent_id}", response_model=AgentConfigResponse)
async def update_agent(
        agent_id: int,
        agent_data: AgentConfigCreate,
        current_user: User = Depends(get_current_admin_user),
        db: Session = Depends(get_db)
):
    """更新智能体（管理员）"""
    service = AgentService(db)

    try:
        agent = service.update_agent(agent_id, agent_data)
        return agent
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
        agent_id: int,
        current_user: User = Depends(get_current_admin_user),
        db: Session = Depends(get_db)
):
    """删除智能体（管理员）"""
    service = AgentService(db)

    success = service.delete_agent(agent_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="智能体不存在"
        )