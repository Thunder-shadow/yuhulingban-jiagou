# app/utils/formatters.py
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class ResponseFormatter:
    """响应格式化器"""

    @staticmethod
    def format_agent_response(
            response: str,
            max_length: int = 150,
            format_rules: str = "旁白无需括号，每条旁白与独白必须换行"
    ) -> str:
        """格式化智能体响应"""
        if not response:
            return ""

        # 清理多余空格和换行
        response = re.sub(r'\s+', ' ', response).strip()

        # 检查并限制长度（中文字符）
        chinese_chars = ResponseFormatter.count_chinese_characters(response)
        if chinese_chars > max_length:
            response = ResponseFormatter.truncate_text(response, max_length)

        # 应用格式规则
        if "旁白无需括号" in format_rules:
            response = ResponseFormatter.format_narration(response)

        if "每条旁白与独白必须换行" in format_rules:
            response = ResponseFormatter.ensure_line_breaks(response)

        return response

    @staticmethod
    def format_narration(text: str) -> str:
        """格式化旁白"""
        # 处理各种括号格式
        bracket_patterns = [
            r'\*\((.*?)\)\*',  # *(...)*
            r'（(.*?)）',  # （...）
            r'\((.*?)\)',  # (...)
            r'【(.*?)】',  # 【...】
            r'\[(.*?)\]',  # [...]
        ]

        for pattern in bracket_patterns:
            text = re.sub(pattern, r'*\1*', text)

        # 确保旁白有正确的星号
        lines = text.split('\n')
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith('"') and not line.startswith('*'):
                # 如果没有引号也不是旁白，可能是没有标点的对话
                if any(punc in line for punc in ['。', '！', '？', '.', '!', '?']):
                    # 有标点，可能是普通叙述
                    formatted_lines.append(f"*{line}*")
                else:
                    # 没有标点，可能是对话
                    formatted_lines.append(f'"{line}"')
            else:
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    @staticmethod
    def ensure_line_breaks(text: str) -> str:
        """确保旁白和对话分行"""
        lines = text.split('\n')
        result = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否包含混合内容
            if '"' in line and '*' in line:
                # 分离对话和旁白
                parts = re.split(r'(\*.*?\*|".*?")', line)
                for part in parts:
                    if part and part.strip():
                        result.append(part.strip())
            else:
                result.append(line)

        return '\n'.join(result)

    @staticmethod
    def truncate_text(text: str, max_chinese_chars: int) -> str:
        """智能截断文本"""
        # 找到合适的截断位置
        sentences = re.split(r'([。！？.!?])', text)
        truncated = ""

        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]

            new_text = truncated + sentence
            if ResponseFormatter.count_chinese_characters(new_text) > max_chinese_chars:
                break
            truncated = new_text

        # 如果截断后太短，至少保留一些内容
        if ResponseFormatter.count_chinese_characters(truncated) < max_chinese_chars * 0.3:
            # 直接按字符数截断
            char_count = 0
            truncated = ""
            for char in text:
                if '\u4e00-\u9fff' in char:
                    char_count += 1
                truncated += char
                if char_count >= max_chinese_chars:
                    break

        if len(truncated) < len(text):
            truncated = truncated.rstrip('，。！？,.!?') + "..."

        return truncated

    @staticmethod
    def count_chinese_characters(text: str) -> int:
        """计算中文字符数"""
        return len(re.findall(r'[\u4e00-\u9fff]', text))

    @staticmethod
    def format_timestamp(timestamp: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化时间戳"""
        return timestamp.strftime(format_str)

    @staticmethod
    def format_user_info(user_info: Dict[str, Any]) -> str:
        """格式化用户信息"""
        parts = []

        if name := user_info.get('name'):
            parts.append(f"称呼: {name}")

        if gender := user_info.get('gender'):
            parts.append(f"性别: {gender}")

        if traits := user_info.get('traits'):
            if isinstance(traits, str):
                parts.append(f"特征: {traits}")
            elif isinstance(traits, list):
                parts.append(f"特征: {', '.join(traits)}")

        return "\n".join(parts) if parts else "无用户信息"


class JSONFormatter:
    """JSON格式化器"""

    @staticmethod
    def safe_dumps(data: Any, indent: int = 2) -> str:
        """安全序列化JSON"""

        def default_converter(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            else:
                return str(obj)

        try:
            return json.dumps(data, indent=indent, ensure_ascii=False, default=default_converter)
        except Exception:
            return str(data)

    @staticmethod
    def safe_loads(json_str: str) -> Any:
        """安全解析JSON"""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试修复常见的JSON格式问题
            fixed = JSONFormatter.fix_json(json_str)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                return {"raw": json_str}

    @staticmethod
    def fix_json(json_str: str) -> str:
        """修复常见的JSON格式问题"""
        # 修复单引号
        fixed = re.sub(r"(?<!\\)'", '"', json_str)

        # 修复没有引号的键
        fixed = re.sub(r'(\s*)(\w+)(\s*):', r'\1"\2"\3:', fixed)

        # 修复尾随逗号
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)

        return fixed

    @staticmethod
    def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
        """从文本中提取JSON"""
        # 查找JSON对象
        json_pattern = r'\{[\s\S]*\}'
        matches = re.findall(json_pattern, text)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None