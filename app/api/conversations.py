# app/api/conversations.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import ConversationResponse, MessageResponse
from app.services.conversation_service import ConversationService
from app.services.chat_service import ChatService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        agent_id: Optional[int] = None,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """获取对话列表"""
    service = ConversationService(db)

    conversations = service.get_user_conversations(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

    # 如果指定了智能体，进行过滤
    if agent_id:
        conversations = [c for c in conversations if c.agent_id == agent_id]

    return conversations


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
        conversation_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """获取对话详情"""
    service = ConversationService(db)

    conversation = service.get_conversation(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )

    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
        conversation_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """删除对话"""
    service = ConversationService(db)

    success = service.delete_conversation(conversation_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
        conversation_id: int,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """获取对话消息"""
    service = ChatService(db)

    try:
        messages = service.get_conversation_messages(
            conversation_id=conversation_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        return messages
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/{conversation_id}/title", response_model=ConversationResponse)
async def update_conversation_title(
        conversation_id: int,
        title: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """更新对话标题"""
    service = ConversationService(db)

    try:
        conversation = service.update_conversation_title(conversation_id, title)
        return conversation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{conversation_id}/continue", response_model=dict)
async def continue_conversation(
        conversation_id: int,
        initial_message: Optional[str] = None,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """继续对话"""
    service = ChatService(db)

    try:
        result = service.continue_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
            initial_message=initial_message
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/agent/{agent_id}", response_model=ConversationResponse)
async def create_conversation_with_agent(
        agent_id: int,
        title: Optional[str] = None,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """创建与指定智能体的对话"""
    service = ConversationService(db)

    try:
        conversation = service.create_conversation(
            user_id=current_user.id,
            agent_id=agent_id,
            title=title
        )
        return conversation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )