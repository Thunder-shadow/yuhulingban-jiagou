# app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import json
import asyncio

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, AgentConfig
from app.schemas import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.agents.agent_factory import AgentFactory

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
        chat_request: ChatRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """聊天接口"""
    service = ChatService(db)

    try:
        result = await service.process_chat(
            user_id=current_user.id,
            agent_name=None,  # 这里需要指定agent_name或从请求中获取
            message=chat_request.message,
            conversation_id=chat_request.conversation_id,
            user_info=chat_request.user_info or {
                "name": current_user.username,
                "gender": "unknown"
            }
        )

        return ChatResponse(
            response=result["response"],
            conversation_id=result["conversation_id"],
            agent_name=result["agent_name"],
            current_stage=result["current_stage"],
            message_id=result["message_id"],
            timestamp=result["timestamp"]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.websocket("/ws/{agent_name}")
async def websocket_chat(
        websocket: WebSocket,
        agent_name: str,
        db: Session = Depends(get_db)
):
    """WebSocket聊天接口"""
    await websocket.accept()

    try:
        # 等待身份验证
        auth_data = await websocket.receive_json()
        token = auth_data.get("token")

        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 验证令牌（简化版，实际需要完整验证）
        from app.security import security_manager
        payload = security_manager.decode_token(token)
        if not payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user_id = payload.get("user_id")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 获取智能体
        agent = db.query(AgentConfig).filter(AgentConfig.name == agent_name).first()
        if not agent:
            await websocket.send_json({
                "type": "error",
                "message": f"智能体 '{agent_name}' 不存在"
            })
            await websocket.close()
            return

        # 创建聊天服务
        service = ChatService(db)

        # 创建或获取对话
        from app.services.conversation_service import ConversationService
        conv_service = ConversationService(db)
        conversation = conv_service.create_conversation(user.id, agent.id)

        await websocket.send_json({
            "type": "connected",
            "conversation_id": conversation.id,
            "agent_name": agent.display_name
        })

        while True:
            # 接收消息
            data = await websocket.receive_json()

            if data.get("type") == "message":
                message = data.get("content", "")

                if message.lower() == "/exit":
                    await websocket.send_json({
                        "type": "system",
                        "message": "对话结束"
                    })
                    break

                # 处理消息
                result = await service.process_chat(
                    user_id=user.id,
                    agent_name=agent_name,
                    message=message,
                    conversation_id=conversation.id,
                    user_info={"name": user.username, "gender": "unknown"}
                )

                # 发送响应
                await websocket.send_json({
                    "type": "message",
                    "content": result["response"],
                    "conversation_id": result["conversation_id"],
                    "current_stage": result["current_stage"],
                    "timestamp": result["timestamp"]
                })

            elif data.get("type") == "close":
                break

    except WebSocketDisconnect:
        print("WebSocket连接断开")
    except Exception as e:
        print(f"WebSocket错误: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"处理消息时出错: {str(e)}"
        })
    finally:
        await websocket.close()