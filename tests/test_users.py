import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

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


def get_agniya_agent(db: Session) -> AgentConfig:
    """获取阿格尼娅智能体"""
    # 根据你的实际情况修改查询条件
    # 可能是通过 name、display_name 或其他字段

    agniya_agent = db.query(AgentConfig).filter(
        (AgentConfig.name == "agniya") |
        (AgentConfig.display_name == "阿格尼娅")
    ).first()

    if not agniya_agent:
        # 如果找不到阿格尼娅，找第一个可用的智能体
        print("未找到阿格尼娅智能体，使用第一个可用智能体")
        agniya_agent = db.query(AgentConfig).first()

    if not agniya_agent:
        raise Exception("数据库中没有任何智能体配置，请先创建智能体")

    print(f"使用智能体: {agniya_agent.display_name} ({agniya_agent.name})")
    return agniya_agent


async def test_chat(db: Session, user: User, agent: AgentConfig):
    """测试聊天功能"""
    print("\n=== 开始聊天测试 ===")

    chat_service = ChatService(db)

    # 测试消息 - 针对阿格尼娅的对话
    test_messages = [
        "你好，阿格尼娅！",
        "今天过得怎么样？",
        "能给我讲个故事吗？",
        "谢谢你的陪伴！"
    ]

    conversation_id = None

    for i, message in enumerate(test_messages, 1):
        print(f"\n--- 第{i}轮对话 ---")
        print(f"用户: {message}")

        try:
            # 发送消息
            response = await chat_service.process_chat(
                user_id=user.id,
                agent_name=agent.name,  # 使用智能体的 name 字段
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
            import traceback
            traceback.print_exc()
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
            # 创建测试用户
            user = create_test_user(db)

            # 获取阿格尼娅智能体
            agent = get_agniya_agent(db)

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