# configs/constants.py
"""系统常量定义"""

# 关系阶段常量
RELATIONSHIP_STAGES = ["陌生期", "熟悉期", "友好期", "亲密期"]

# 默认输出格式配置
DEFAULT_OUTPUT_FORMAT = {
    "max_length": 150,
    "format_rules": "旁白无需括号，每条旁白与独白必须换行",
    "example": "*他低头看着怀里的猫*\n\"所有靠近我的人都会受伤。\""
}

# 默认模型配置
DEFAULT_MODEL_CONFIG = {
    "provider": "openai_api_compatible",
    "model": "DeepSeek-V3",
    "temperature": 1.0,
    "top_p": 0.4,
    "presence_penalty": 0.2,
    "max_tokens": 1000
}

# 用户状态枚举
USER_STATUS_CHOICES = ["active", "inactive", "suspended"]

# 用户角色枚举
USER_ROLE_CHOICES = ["user", "admin", "moderator"]

# 订阅状态枚举
SUBSCRIPTION_STATUS_CHOICES = ["none", "active", "expired", "cancelled"]