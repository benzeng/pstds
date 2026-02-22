# pstds/config.py
# 配置加载模块

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """
    配置管理类

    从 config/user.yaml 和 config/default.yaml 加载配置
    """

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        config_dir = Path(__file__).parent.parent / "config"

        # 加载默认配置
        default_config = config_dir / "default.yaml"
        if default_config.exists():
            with open(default_config, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}

        # 合并用户配置
        user_config = config_dir / "user.yaml"
        if user_config.exists():
            with open(user_config, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}
                # 深度合并配置
                self._deep_merge(self._config, user_cfg)

    def _deep_merge(self, base: Dict, update: Dict) -> None:
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键，支持点号分隔的路径（如 'api_keys.alpha_vantage'）
            default: 默认值

        Returns:
            配置值
        """
        if "." in key:
            parts = key.split(".")
            value = self._config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value if value != self._config else default
        else:
            return self._config.get(key, default)

    def get_api_key(self, service: str) -> Optional[str]:
        """
        获取 API key

        Args:
            service: 服务名称（openai, anthropic, alpha_vantage 等）

        Returns:
            API key 或 None
        """
        key_path = f"api_keys.{service}"
        return self.get(key_path)

    def get_mongodb_connection_string(self) -> str:
        """获取 MongoDB 连接字符串"""
        return self.get("mongodb.connection_string", "mongodb://localhost:27017/")

    def get_mongodb_database_name(self) -> str:
        """获取 MongoDB 数据库名"""
        return self.get("mongodb.database_name", "pstds")

    def get_llm_config(self) -> Dict[str, Any]:
        """获取 LLM 配置"""
        return self.get("llm", {})

    def get_data_config(self) -> Dict[str, Any]:
        """获取数据源配置"""
        return self.get("data", {})


# 全局配置实例
_global_config: Optional[Config] = None


def get_config() -> Config:
    """
    获取全局配置实例

    Returns:
        Config 实例
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def reload_config() -> None:
    """重新加载配置"""
    global _global_config
    _global_config = None
