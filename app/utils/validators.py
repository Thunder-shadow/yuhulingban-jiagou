# app/utils/validators.py
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from email_validator import validate_email, EmailNotValidError


class InputValidator:
    """输入验证器"""

    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """验证用户名"""
        if not username or len(username.strip()) == 0:
            return False, "用户名不能为空"

        username = username.strip()

        # 长度检查
        if len(username) < 3:
            return False, "用户名至少3个字符"
        if len(username) > 50:
            return False, "用户名最多50个字符"

        # 字符检查（只允许字母、数字、下划线、中文）
        if not re.match(r'^[\w\u4e00-\u9fff]+$', username):
            return False, "用户名只能包含字母、数字、下划线和中文"

        # 保留名称检查
        reserved_names = ['admin', 'root', 'system', 'test', 'user', 'guest']
        if username.lower() in reserved_names:
            return False, "该用户名不可用"

        return True, ""

    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        """验证邮箱"""
        if not email or len(email.strip()) == 0:
            return False, "邮箱不能为空"

        email = email.strip().lower()

        try:
            # 验证邮箱格式
            email_info = validate_email(email, check_deliverability=False)
            normalized_email = email_info.normalized

            # 检查常见邮箱服务商
            common_domains = ['gmail.com', 'qq.com', '163.com', '126.com',
                              'outlook.com', 'hotmail.com', 'yahoo.com']
            domain = normalized_email.split('@')[1]
            if domain not in common_domains:
                # 检查是否为有效域名格式
                if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
                    return False, "邮箱域名格式不正确"

            return True, normalized_email

        except EmailNotValidError as e:
            return False, str(e)

    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """验证密码"""
        if not password:
            return False, "密码不能为空"

        if len(password) < 8:
            return False, "密码至少8个字符"

        if len(password) > 100:
            return False, "密码最多100个字符"

        # 检查密码强度
        checks = {
            "至少一个小写字母": r'[a-z]',
            "至少一个大写字母": r'[A-Z]',
            "至少一个数字": r'\d',
            "至少一个特殊字符": r'[!@#$%^&*(),.?":{}|<>]'
        }

        missing = []
        for requirement, pattern in checks.items():
            if not re.search(pattern, password):
                missing.append(requirement)

        if missing:
            return False, f"密码需要包含: {', '.join(missing)}"

        # 检查常见弱密码
        weak_passwords = [
            'password', '123456', 'qwerty', 'admin', 'welcome',
            'password123', 'abc123', '111111', '000000'
        ]

        if password.lower() in weak_passwords:
            return False, "密码过于简单"

        return True, ""

    @staticmethod
    def validate_agent_name(name: str) -> tuple[bool, str]:
        """验证智能体名称"""
        if not name or len(name.strip()) == 0:
            return False, "智能体名称不能为空"

        name = name.strip()

        # 长度检查
        if len(name) < 2:
            return False, "智能体名称至少2个字符"
        if len(name) > 100:
            return False, "智能体名称最多100个字符"

        # 字符检查
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            return False, "智能体名称只能包含字母、数字、下划线和连字符"

        # 保留名称检查
        reserved_names = ['api', 'admin', 'system', 'test', 'user']
        if name.lower() in reserved_names:
            return False, "该名称不可用"

        return True, ""

    @staticmethod
    def validate_character_profile(profile: Dict[str, Any]) -> tuple[bool, str]:
        """验证角色配置"""
        if not profile:
            return False, "角色配置不能为空"

        # 检查必需字段
        required_fields = ['name', 'personality']
        for field in required_fields:
            if field not in profile:
                return False, f"缺少必需字段: {field}"

        # 验证字段类型
        if not isinstance(profile.get('name', ''), str):
            return False, "角色名称必须是字符串"

        if not isinstance(profile.get('personality', ''), str):
            return False, "性格描述必须是字符串"

        # 验证可选字段类型
        list_fields = ['traits', 'skills', 'quirks']
        for field in list_fields:
            if field in profile and not isinstance(profile[field], list):
                return False, f"{field}必须是列表"

        # 验证武器字段
        if 'weapon' in profile and not isinstance(profile['weapon'], dict):
            return False, "武器信息必须是字典"

        # 验证队友字段
        if 'teammates' in profile:
            if not isinstance(profile['teammates'], list):
                return False, "队友信息必须是列表"
            for tm in profile['teammates']:
                if not isinstance(tm, dict):
                    return False, "每个队友信息必须是字典"

        return True, ""

    @staticmethod
    def sanitize_input(text: str, max_length: int = 5000) -> str:
        """清理输入文本"""
        if not text:
            return ""

        # 限制长度
        if len(text) > max_length:
            text = text[:max_length]

        # 移除危险字符（简化版）
        dangerous_patterns = [
            r'<script.*?>.*?</script>',  # 移除脚本标签
            r'on\w+=".*?"',  # 移除事件处理器
            r'javascript:',  # 移除JavaScript协议
            r'data:',  # 移除data协议
            r'vbscript:',  # 移除VBScript协议
        ]

        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # 转义HTML特殊字符
        html_escapes = {
            '<': '&lt;',
            '>': '&gt;',
            '&': '&amp;',
            '"': '&quot;',
            "'": '&#39;'
        }

        for char, escape in html_escapes.items():
            text = text.replace(char, escape)

        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    @staticmethod
    def validate_message_content(content: str) -> tuple[bool, str]:
        """验证消息内容"""
        if not content or len(content.strip()) == 0:
            return False, "消息内容不能为空"

        content = content.strip()

        # 长度检查
        if len(content) > 5000:
            return False, "消息内容最多5000字符"

        # 检查是否全是空白字符
        if re.match(r'^\s*$', content):
            return False, "消息内容不能全是空白字符"

        # 检查恶意内容模式
        malicious_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # URL
            r'[\w\.-]+@[\w\.-]+\.\w+',  # 邮箱
            r'\d{3}-\d{3}-\d{4}',  # 电话号码
            r'\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}',  # 信用卡
        ]

        for pattern in malicious_patterns:
            if re.search(pattern, content):
                # 允许URL和邮箱，但记录警告
                print(f"警告: 消息可能包含敏感信息: {content[:50]}...")
                break

        return True, ""