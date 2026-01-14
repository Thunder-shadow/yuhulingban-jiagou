# app/agents/character_agent.py
from typing import Dict, List, Optional, Any
import re
import json

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.models import AgentConfig, AgentState
from app.agents.schema_manager import AgentSchemaManager


class CharacterAgent:
    """角色智能体"""

    def __init__(self, agent_config: AgentConfig, base_url: str, api_key: str):
        self.config = agent_config
        self.agent_id = agent_config.id
        self.name = agent_config.name

        # 初始化模型配置
        model_config = agent_config.model_config or {}
        self.llm = ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model=model_config.get("model", "DeepSeek-V3.1-Terminus"),
            temperature=model_config.get("temperature", 1.0),
            top_p=model_config.get("top_p", 0.4),
            presence_penalty=model_config.get("presence_penalty", 0.2),
            max_tokens=model_config.get("max_tokens", 1000),
        )

        # 模式管理器
        self.schema_manager = AgentSchemaManager()

        # 格式化角色配置
        self.character_profile = self.schema_manager.validate_and_normalize(
            agent_config.name, agent_config.character_profile
        )

    def build_system_prompt(self, stage: str, agent_state: Optional[AgentState] = None) -> str:
        """构建系统提示词"""
        profile = self.character_profile
        output_format = self.config.output_format or {}

        # 阶段描述
        stage_descriptions = {
            "陌生期": "警惕、正式、保持距离，对用户持有敌意或怀疑",
            "熟悉期": "稍微放松，但仍保持礼貌，开始对用户有所了解",
            "友好期": "更加信任，愿意分享想法，可能有复杂的感情",
            "亲密期": "非常信任，可能展现脆弱一面，关系深厚"
        }

        # 记忆提取
        memories_text = ""
        if agent_state and agent_state.key_memories:
            memories_text = "\n## 重要记忆\n"
            for i, memory in enumerate(agent_state.key_memories[-3:], 1):  # 最近3条
                memories_text += f"{i}. {memory}\n"

        # 用户特征
        traits_text = ""
        if agent_state and agent_state.user_traits:
            traits_text = "\n## 用户特征\n"
            for key, value in agent_state.user_traits.items():
                traits_text += f"- {key}: {value}\n"

        prompt = f"""# 角色设定
你正在扮演角色：{profile.get('name', '未知角色')}

## 基本信息
性格：{profile.get('personality', '')}
性别：{profile.get('gender', '')}
年龄：{profile.get('age', '')}
外貌：{profile.get('appearance', '')}
服装：{profile.get('clothing', '')}

## 能力与特质
技能：{', '.join(profile.get('skills', []))}
特质：{', '.join(profile.get('traits', []))}

## 背景故事
{self.config.background_story or ''}

## 当前关系阶段：{stage}
{stage_descriptions.get(stage, '')}

{memories_text}
{traits_text}

## 输出要求
1. 回复长度：不超过{output_format.get('max_length', 150)}字
2. 格式：{output_format.get('format_rules', '')}
3. 根据当前阶段演绎角色的神态、动作和情绪
4. 参考示例格式：
{output_format.get('example', '*动作描述* "对话内容"')}

## 重要提示
- 保持角色一致性，不要跳出角色
- 根据阶段调整语气和态度
- 自然地推进剧情发展
"""

        return prompt.strip()

    def generate_response(
            self,
            user_input: str,
            user_info: Dict[str, Any],
            agent_state: AgentState,
            conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成响应"""
        from datetime import datetime

        # 构建消息历史
        messages = []

        # 添加系统提示
        system_prompt = self.build_system_prompt(agent_state.current_stage, agent_state)
        messages.append(SystemMessage(content=system_prompt))

        # 添加上下文历史（最近5条）
        for msg in conversation_history[-5:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        # 添加当前用户输入
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_prompt = f"""当前时间：{current_time}

用户信息：
- 称呼：{user_info.get('name', '用户')}
- 性别：{user_info.get('gender', '未知')}
- 特征：{user_info.get('traits', '')}

用户消息：{user_input}

请以{self.character_profile.get('name', '角色')}的身份回复："""

        messages.append(HumanMessage(content=user_prompt))

        try:
            # 调用模型
            response = self.llm.invoke(messages)

            # 格式化响应
            formatted_response = self.format_response(response.content)

            # 提取信息用于记忆
            extracted_info = self.extract_info_from_response(formatted_response, user_input)

            return {
                "response": formatted_response,
                "raw_response": response.content,
                "extracted_info": extracted_info,
                "model_used": self.llm.model_name,
                "timestamp": current_time
            }

        except Exception as e:
            return {
                "response": f"抱歉，我遇到了一些问题：{str(e)}",
                "raw_response": "",
                "extracted_info": {},
                "model_used": self.llm.model_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def format_response(self, response: str) -> str:
        """格式化响应"""
        # 清理多余空格
        response = re.sub(r'\s+', ' ', response).strip()

        # 检查长度
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', response))
        max_length = self.config.output_format.get('max_length', 150) if self.config.output_format else 150

        if chinese_chars > max_length:
            # 在句子结尾处截断
            sentences = re.split(r'([。！？.!?])', response)
            truncated = ""
            for i in range(0, len(sentences), 2):
                if i + 1 < len(sentences):
                    sentence = sentences[i] + sentences[i + 1]
                else:
                    sentence = sentences[i]

                new_text = truncated + sentence
                if len(re.findall(r'[\u4e00-\u9fff]', new_text)) > max_length:
                    break
                truncated = new_text

            response = truncated + "..." if len(truncated) < len(response) else truncated

        # 确保旁白格式
        lines = response.split('\n')
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith('*') and line.endswith('*'):
                formatted_lines.append(f"*{line[1:-1].strip()}*")
            elif line and not line.startswith('"'):
                formatted_lines.append(f'"{line}"')
            else:
                formatted_lines.append(line)

        return '\n'.join(filter(None, formatted_lines))

    def extract_info_from_response(self, response: str, user_input: str) -> Dict[str, Any]:
        """从响应中提取信息"""
        extracted = {
            "topics": [],
            "emotions": [],
            "key_points": []
        }

        # 情感检测
        emotion_keywords = {
            "愤怒": ["愤怒", "生气", "发怒", "怒火", "气愤"],
            "悲伤": ["悲伤", "难过", "伤心", "哭泣", "悲痛"],
            "喜悦": ["高兴", "开心", "喜悦", "微笑", "快乐"],
            "矛盾": ["矛盾", "纠结", "犹豫", "挣扎", "困惑"],
            "恐惧": ["害怕", "恐惧", "惊慌", "担心", "畏惧"]
        }

        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in response:
                    extracted["emotions"].append(emotion)
                    break

        # 话题提取
        topic_keywords = ["剑", "战斗", "和平", "队友", "回忆", "魔王", "王国",
                          "魔法", "使命", "复仇", "爱情", "友谊", "牺牲"]
        for keyword in topic_keywords:
            if keyword in response or keyword in user_input:
                extracted["topics"].append(keyword)

        # 关键点提取（简单的启发式规则）
        if any(keyword in response for keyword in ["永远", "承诺", "誓言", "约定"]):
            extracted["key_points"].append("重要承诺")
        if any(keyword in response for keyword in ["秘密", "真相", "隐藏", "揭露"]):
            extracted["key_points"].append("秘密揭示")
        if any(keyword in response for keyword in ["对不起", "抱歉", "原谅", "悔恨"]):
            extracted["key_points"].append("道歉或原谅")

        return extracted