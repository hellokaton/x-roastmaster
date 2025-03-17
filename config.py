import logging
import os
from pathlib import Path
from typing import Any, Optional, TypeVar

from dotenv import load_dotenv

# 加载.env文件
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

T = TypeVar('T')

class Env:
    """环境变量配置管理器"""
    
    @staticmethod
    def get(key: str, default: Any = None) -> str:
        """获取字符串类型的环境变量"""
        value = os.getenv(key)
        if value is None:
            if default is None:
                raise ValueError(f"缺少必需的环境变量: {key}")
            return default
        return value
    
    @staticmethod
    def get_bool(key: str, default: Optional[bool] = None) -> bool:
        """获取布尔类型的环境变量"""
        value = os.getenv(key)
        if value is None:
            if default is None:
                raise ValueError(f"缺少必需的环境变量: {key}")
            return default
        return value.lower() in ('true', 'yes', '1', 'y')
    
    @staticmethod
    def get_int(key: str, default: Optional[int] = None) -> int:
        """获取整数类型的环境变量"""
        value = os.getenv(key)
        if value is None:
            if default is None:
                raise ValueError(f"缺少必需的环境变量: {key}")
            return default
        return int(value)
    
    @staticmethod
    def get_float(key: str, default: Optional[float] = None) -> float:
        """获取浮点数类型的环境变量"""
        value = os.getenv(key)
        if value is None:
            if default is None:
                raise ValueError(f"缺少必需的环境变量: {key}")
            return default
        return float(value)


# Twitter API 配置
X_API_KEY = Env.get("X_API_KEY")

# OpenAI 配置
OPENAI_URL = Env.get("OPENAI_URL", "https://openrouter.ai/api/v1")
OPENAI_KEY = Env.get("OPENAI_KEY")
OPENAI_MODEL = Env.get("OPENAI_MODEL", "deepseek/deepseek-r1")

# 缓存配置
ENABLE_CACHE = Env.get_bool("ENABLE_CACHE", True)
CACHE_EXPIRE_MINUTES = Env.get_int("CACHE_EXPIRE_MINUTES", 30)

# 日志级别
LOG_LEVEL = Env.get_int("LOG_LEVEL", logging.INFO)
