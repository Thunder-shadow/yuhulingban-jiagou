import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.sql.functions import user

load_dotenv()
# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, init_database
from app.models import Base, User, AgentConfig, Conversation, Message
from app.services.user_service import UserService
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService
from app.security import security_manager
from datetime import datetime


def create_test_user(db: Session) -> User:
    """创建测试用户"""
    from app.schemas import UserCreate  # 添加导入

    user_service = UserService(db)

    # 检查用户是否已存在
    existing_user = db.query(User).filter(User.username == "test_user").first()
    if existing_user:
        print("测试用户已存在")
        return existing_user

        # 创建 UserCreate 对象
    user_data = UserCreate(
        username="test_user",
        email="2956226494@qq.com",
        password="test123456"
    )

    # 传递 UserCreate 对象而不是单独的参数
    user = user_service.create_user(user_data)
    print(f"创建测试用户: {user.username}")
    return user


def create_test_agent(db: Session, user: User) -> AgentConfig:
    """创建测试智能体（适配硅基流动）"""
    from app.schemas import AgentConfigCreate  # 添加导入

    agent_service = AgentService(db)

    # 检查智能体是否已存在
    existing_agent = db.query(AgentConfig).filter(AgentConfig.name == "test_agent").first()
    if existing_agent:
        print("测试智能体已存在")
        return existing_agent

        # 创建智能体配置字典
    agent_config_dict = {
        "name": "test_agent",
        "display_name": "测试助手",
        #"description": "用于本地测试的智能助手",
        "icon": "🤖",
        "icon_background": "#E8F4FD",
        "character_profile": {
            "name": "小助手",
            "personality": "友好、耐心、乐于助人",
            "gender": "无性别",
            "age": "永生",
            "race": "AI",
            "appearance": "虚拟形象",
            "clothing": "简约风格",
            "traits": ["聪明", "友善", "耐心"],
            "skills": ["问答", "聊天", "帮助"],
            "goals": "帮助用户解决问题"
        },
        "opening_statement": "*微笑着向你挥手*\n\"你好！我是小助手，很高兴为你服务！\"",
        "background_story": "我是一个专门为帮助用户而设计的AI助手。",
        "model_config": {
            "provider": "openai_api_compatible",
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "temperature": 0.7,
            "top_p": 0.5,
            "presence_penalty": 0.1,
            "max_tokens": 800
        },
        "stages": ["陌生期", "熟悉期", "友好期", "亲密期"],
        "output_format": {
            "max_length": 150,
            "format_rules": "自然对话，无需特殊格式",
            "example": "\"你好！有什么可以帮助你的吗？\""
        }
    }

    # 转换为 AgentConfigCreate 对象
    agent_data = AgentConfigCreate(**agent_config_dict)

    # 传递 AgentConfigCreate 对象
    agent = agent_service.create_agent(agent_data, user.id)
    print(f"创建测试智能体: {agent.display_name}")
    return agent


async def test_chat(db: Session, user: User, agent: AgentConfig):
    """测试聊天功能"""
    print("\n=== 开始聊天测试 ===")

    chat_service = ChatService(db)

    # 测试消息
    test_messages = [
        "你好，你是谁？",
        "你能帮我做什么？",
        "今天天气怎么样？",
        "谢谢你的帮助"
    ]

    conversation_id = None

    for i, message in enumerate(test_messages, 1):
        print(f"\n--- 第{i}轮对话 ---")
        print(f"用户: {message}")

        try:
            # 发送消息
            response = await chat_service.process_chat(
                user_id=user.id,
                agent_name=agent.name,
                message=message,
                conversation_id=conversation_id,
                user_info=None
            )

            print(f"助手: {response['response']}")
            print(f"当前阶段: {response['current_stage']}")
            print(f"对话ID: {response['conversation_id']}")

            # 保存对话ID用于后续消息
            conversation_id = response['conversation_id']

        except Exception as e:
            print(f"聊天出错: {e}")
            break


def main():
    """主测试函数"""
    print("=== 本地测试脚本 ===")

    # 检查环境变量
    if not os.getenv("LLM_API_KEY"):
        print("错误: 请设置 LLM_API_KEY 环境变量")
        return

    try:
        # 初始化数据库
        print("初始化数据库...")
        init_database()
        print("数据库初始化完成")

        # 创建数据库会话
        db = SessionLocal()

        try:
            # 创建测试数据
            user = create_test_user(db)
            agent = create_test_agent(db, user)

            # 提交创建的数据
            db.commit()

            # 测试聊天
            asyncio.run(test_chat(db, user, agent))

        finally:
            db.close()

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()