# app/agents/schema_manager.py
from typing import Dict, Any, Optional, List
import json
from pydantic import BaseModel, Field, validator
from enum import Enum


class CharacterGender(str, Enum):
    MALE = "男性"
    FEMALE = "女性"
    OTHER = "其他"
    UNKNOWN = "未知"


class CharacterSchema(BaseModel):
    """角色基础模式"""
    name: str = Field(..., description="角色名称")
    personality: str = Field(..., description="性格描述")
    gender: Optional[CharacterGender] = Field(CharacterGender.UNKNOWN, description="性别")
    age: Optional[str] = Field(None, description="年龄")
    race: Optional[str] = Field(None, description="种族")
    appearance: Optional[str] = Field(None, description="外貌描述")
    clothing: Optional[str] = Field(None, description="服装描述")

    # 验证器
    @validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('角色名称不能为空')
        return v.strip()


class AdvancedCharacterSchema(CharacterSchema):
    """高级角色模式"""
    traits: List[str] = Field(default_factory=list, description="性格特质")
    skills: List[str] = Field(default_factory=list, description="技能列表")
    weapon: Optional[Dict[str, Any]] = Field(None, description="武器信息")
    teammates: Optional[List[Dict[str, Any]]] = Field(None, description="队友信息")
    goals: Optional[str] = Field(None, description="目标")
    quirks: Optional[List[str]] = Field(default_factory=list, description="怪癖习惯")
    backstory: Optional[str] = Field(None, description="背景故事")

    # 扩展字段
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="自定义字段")


class WeaponSchema(BaseModel):
    """武器模式"""
    name: str = Field(..., description="武器名称")
    type: str = Field(..., description="武器类型")
    abilities: Optional[str] = Field(None, description="武器能力")
    origin: Optional[str] = Field(None, description="起源")
    appearance: Optional[str] = Field(None, description="外观")
    limitations: Optional[str] = Field(None, description="限制")


class TeammateSchema(BaseModel):
    """队友模式"""
    name: str = Field(..., description="队友名称")
    role: str = Field(..., description="角色/职业")
    relationship: Optional[str] = Field(None, description="与主角的关系")
    status: Optional[str] = Field("alive", description="状态: alive/dead/missing")


class AgentSchemaManager:
    """智能体模式管理器"""

    def __init__(self):
        self.schema_registry = {
            "default": AdvancedCharacterSchema,
            "fantasy": self._create_fantasy_schema,
            "sci_fi": self._create_scifi_schema,
            "modern": self._create_modern_schema,
            "historical": self._create_historical_schema,
        }

        self.field_mappings = {
            "基础信息": ["name", "personality", "gender", "age", "race"],
            "外貌服装": ["appearance", "clothing"],
            "性格特质": ["traits", "quirks"],
            "能力技能": ["skills"],
            "装备道具": ["weapon"],
            "人际关系": ["teammates"],
            "目标背景": ["goals", "backstory"]
        }

    def validate_and_normalize(
            self,
            agent_name: str,
            raw_profile: Any
    ) -> Dict[str, Any]:
        """验证并标准化角色配置"""

        try:
            # 解析原始数据
            if isinstance(raw_profile, str):
                try:
                    profile = json.loads(raw_profile)
                except json.JSONDecodeError:
                    # 如果不是JSON，尝试其他格式
                    profile = {"raw": raw_profile}
            else:
                profile = raw_profile

            if not isinstance(profile, dict):
                profile = {"content": str(profile)}

            # 检测智能体类型
            agent_type = self._detect_agent_type(profile)

            # 获取或创建模式
            if agent_type in self.schema_registry:
                schema_func = self.schema_registry[agent_type]
                if callable(schema_func):
                    schema_class = schema_func()
                else:
                    schema_class = schema_func
            else:
                schema_class = AdvancedCharacterSchema

            # 转换字段名
            normalized_profile = self._normalize_field_names(profile)

            # 验证模式
            try:
                validated = schema_class(**normalized_profile)
                result = validated.dict(exclude_none=True)

                # 保留原始自定义字段
                if hasattr(validated, 'custom_fields'):
                    result.update(validated.custom_fields)

                # 添加元数据
                result["_schema_type"] = agent_type
                result["_validated"] = True

                return result

            except Exception as validation_error:
                # 如果验证失败，返回原始数据并添加警告
                print(f"警告: 智能体 {agent_name} 配置验证失败: {validation_error}")
                profile["_validation_warning"] = str(validation_error)
                profile["_schema_type"] = "raw"
                profile["_validated"] = False
                return profile

        except Exception as e:
            print(f"错误: 处理智能体 {agent_name} 配置时出错: {e}")
            return {
                "name": agent_name,
                "personality": "配置解析失败",
                "_error": str(e),
                "_validated": False
            }

    def _detect_agent_type(self, profile: Dict[str, Any]) -> str:
        """检测智能体类型"""
        # 基于关键词检测
        fantasy_keywords = ["魔法", "剑", "骑士", "精灵", "龙", "魔王", "勇者"]
        scifi_keywords = ["科技", "太空", "机器人", "AI", "未来", "飞船", "星际"]
        modern_keywords = ["现代", "都市", "学校", "职场", "日常"]
        historical_keywords = ["历史", "古代", "王朝", "皇帝", "将军"]

        # 检查字段内容
        content_str = json.dumps(profile, ensure_ascii=False).lower()

        if any(keyword in content_str for keyword in fantasy_keywords):
            return "fantasy"
        elif any(keyword in content_str for keyword in scifi_keywords):
            return "sci_fi"
        elif any(keyword in content_str for keyword in modern_keywords):
            return "modern"
        elif any(keyword in content_str for keyword in historical_keywords):
            return "historical"
        else:
            return "default"

    def _normalize_field_names(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """标准化字段名"""
        normalized = {}
        field_mapping = {
            # 中文到英文映射
            "姓名": "name", "名字": "name", "角色名": "name",
            "性格": "personality", "个性": "personality",
            "性别": "gender", "sex": "gender",
            "年龄": "age", "年紀": "age",
            "种族": "race", "物种": "race",
            "外貌": "appearance", "长相": "appearance", "外表": "appearance",
            "服装": "clothing", "衣着": "clothing", "打扮": "clothing",
            "特质": "traits", "特点": "traits",
            "技能": "skills", "能力": "skills",
            "武器": "weapon", "装备": "weapon",
            "队友": "teammates", "同伴": "teammates", "伙伴": "teammates",
            "目标": "goals", "目的": "goals",
            "怪癖": "quirks", "习惯": "quirks",
            "背景": "backstory", "故事": "backstory", "经历": "backstory",

            # 英文到英文（确保一致性）
            "personality_traits": "traits",
            "abilities": "skills",
            "companions": "teammates",
            "history": "backstory",
            "apparel": "clothing",
            "looks": "appearance"
        }

        for key, value in profile.items():
            if key in field_mapping:
                normalized[field_mapping[key]] = value
            else:
                # 保持原样
                normalized[key] = value

        return normalized

    def extract_prompt_fields(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """提取构建提示词所需的字段"""
        result = {}

        # 基础信息
        for field in ["name", "personality", "gender", "age", "race",
                      "appearance", "clothing", "goals", "backstory"]:
            if field in profile:
                result[field] = profile[field]

        # 列表字段转换为字符串
        for field in ["traits", "skills", "quirks"]:
            if field in profile and isinstance(profile[field], list):
                result[field] = ", ".join(profile[field])
            elif field in profile:
                result[field] = str(profile[field])

        # 武器信息
        if "weapon" in profile and isinstance(profile["weapon"], dict):
            weapon = profile["weapon"]
            result["weapon_name"] = weapon.get("name", "")
            result["weapon_type"] = weapon.get("type", "")
            result["weapon_abilities"] = weapon.get("abilities", "")

        # 队友信息
        if "teammates" in profile and isinstance(profile["teammates"], list):
            teammates_text = []
            for i, tm in enumerate(profile["teammates"], 1):
                if isinstance(tm, dict):
                    name = tm.get("name", f"队友{i}")
                    role = tm.get("role", "")
                    teammates_text.append(f"{name}: {role}")
                else:
                    teammates_text.append(str(tm))
            result["teammates"] = "\n".join(teammates_text)

        return result

    def _create_fantasy_schema(self):
        """创建奇幻角色模式"""

        class FantasyCharacterSchema(AdvancedCharacterSchema):
            magic_system: Optional[str] = Field(None, description="魔法系统")
            kingdom: Optional[str] = Field(None, description="所属王国")
            title: Optional[str] = Field(None, description="头衔/称号")
            alignment: Optional[str] = Field(None, description="阵营: 善良/中立/邪恶")

            class Config:
                extra = "allow"

        return FantasyCharacterSchema

    def _create_scifi_schema(self):
        """创建科幻角色模式"""

        class SciFiCharacterSchema(AdvancedCharacterSchema):
            tech_level: Optional[str] = Field(None, description="科技水平")
            organization: Optional[str] = Field(None, description="所属组织")
            cybernetics: Optional[List[str]] = Field(default_factory=list, description="义体/改造")
            spaceship: Optional[Dict[str, Any]] = Field(None, description="飞船信息")

            class Config:
                extra = "allow"

        return SciFiCharacterSchema

    def _create_modern_schema(self):
        """创建现代角色模式"""

        class ModernCharacterSchema(AdvancedCharacterSchema):
            occupation: Optional[str] = Field(None, description="职业")
            education: Optional[str] = Field(None, description="教育背景")
            family: Optional[List[str]] = Field(default_factory=list, description="家庭成员")
            hobbies: Optional[List[str]] = Field(default_factory=list, description="爱好")

            class Config:
                extra = "allow"

        return ModernCharacterSchema

    def _create_historical_schema(self):
        """创建历史角色模式"""

        class HistoricalCharacterSchema(AdvancedCharacterSchema):
            era: Optional[str] = Field(None, description="历史时期")
            dynasty: Optional[str] = Field(None, description="朝代")
            social_class: Optional[str] = Field(None, description="社会阶层")
            historical_facts: Optional[List[str]] = Field(default_factory=list, description="历史事实")

            class Config:
                extra = "allow"

        return HistoricalCharacterSchema

    def generate_schema_template(self, agent_type: str = "default") -> Dict[str, Any]:
        """生成模式模板"""
        templates = {
            "default": {
                "name": "角色名称",
                "personality": "详细性格描述",
                "gender": "性别",
                "age": "年龄",
                "race": "种族",
                "appearance": "外貌描述",
                "clothing": "服装描述",
                "traits": ["特质1", "特质2"],
                "skills": ["技能1", "技能2"],
                "goals": "角色目标",
                "backstory": "背景故事"
            },
            "fantasy": {
                "name": "角色名称",
                "personality": "性格描述",
                "gender": "性别",
                "race": "种族（人类/精灵/矮人等）",
                "appearance": "外貌",
                "clothing": "服装盔甲",
                "weapon": {
                    "name": "武器名",
                    "type": "武器类型",
                    "abilities": "特殊能力"
                },
                "magic_system": "魔法系统",
                "kingdom": "所属王国",
                "alignment": "阵营"
            }
        }

        return templates.get(agent_type, templates["default"])