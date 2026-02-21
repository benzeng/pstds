# pstds/llm/factory.py
# 扩展 LLM 工厂 - Phase 3 Task 1

from typing import Optional, Any, Dict
from abc import ABC, abstractmethod

import openai
import anthropic
import google.generativeai as genai

# DeepSeek SDK
try:
    from deepseek import DeepSeek
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False

# DashScope SDK (阿里云)
try:
    import dashscope
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False


class BaseLLMClient(ABC):
    """LLM 客户端基类"""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        self.model = model
        self.base_url = base_url
        self.kwargs = kwargs

    @abstractmethod
    def get_llm(self) -> Any:
        """返回配置的 LLM 实例"""
        pass

    @abstractmethod
    def validate_model(self) -> bool:
        """验证模型是否被支持"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI 兼容客户端（支持 OpenAI、Ollama、XAI 等）"""

    def __init__(self, model: str, base_url: Optional[str] = None, provider: str = "openai", **kwargs):
        super().__init__(model, base_url, **kwargs)
        self.provider = provider

        # 温度参数检查
        assert kwargs.get('temperature', 0.0) == 0.0, "temperature 必须为 0.0"

        # 构建客户端
        if base_url:
            self.client = openai.OpenAI(
                base_url=base_url,
                api_key=kwargs.get('api_key', 'dummy-key')
            )
        else:
            self.client = openai.OpenAI(api_key=kwargs.get('api_key'))

    def get_llm(self) -> Any:
        """返回 OpenAI 兼容的 LLM 实例（temperature=0.0）"""
        return self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,  # 硬编码为 0.0
            **{k: v for k, v in self.kwargs.items() if k not in ['temperature']}
        )

    def validate_model(self) -> bool:
        """验证模型名称"""
        return bool(self.model)


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude 客户端"""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

        # 温度参数检查
        assert kwargs.get('temperature', 0.0) == 0.0, "temperature 必须为 0.0"

        if base_url:
            self.client = anthropic.Anthropic(
                base_url=base_url,
                api_key=kwargs.get('api_key')
            )
        else:
            self.client = anthropic.Anthropic(api_key=kwargs.get('api_key'))

    def get_llm(self) -> Any:
        """返回 Anthropic Claude 实例（temperature=0.0）"""
        return self.client.messages.create(
            model=self.model,
            temperature=0.0,  # 硬编码为 0.0
            **{k: v for k, v in self.kwargs.items() if k not in ['temperature']}
        )

    def validate_model(self) -> bool:
        """验证模型名称"""
        return bool(self.model)


class GoogleClient(BaseLLMClient):
    """Google Gemini 客户端"""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

        # 温度参数检查
        assert kwargs.get('temperature', 0.0) == 0.0, "temperature 必须为 0.0"

        genai.configure(api_key=kwargs.get('api_key'))
        self.client = genai.GenerativeModel(self.model)

    def get_llm(self) -> Any:
        """返回 Google Gemini 实例（temperature=0.0）"""
        return self.client.generate_content(
            temperature=0.0,  # 硬编码为 0.0
            **{k: v for k, v in self.kwargs.items() if k not in ['temperature']}
        )

    def validate_model(self) -> bool:
        """验证模型名称"""
        return bool(self.model)


class DeepSeekClient(BaseLLMClient):
    """DeepSeek 客户端"""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        if not DEEPSEEK_AVAILABLE:
            raise ImportError("deepseek SDK 未安装。请运行: pip install deepseek")

        super().__init__(model, base_url, **kwargs)

        # 温度参数检查
        assert kwargs.get('temperature', 0.0) == 0.0, "temperature 必须为 0.0"

        api_key = kwargs.get('api_key', '')
        if base_url:
            self.client = DeepSeek(api_key=api_key, base_url=base_url)
        else:
            self.client = DeepSeek(api_key=api_key)

    def get_llm(self) -> Any:
        """返回 DeepSeek 实例（temperature=0.0）"""
        return self.client.chat.completions.create(
            model=self.model,
            temperature=0.0,  # 硬编码为 0.0
            **{k: v for k, v in self.kwargs.items() if k not in ['temperature']}
        )

    def validate_model(self) -> bool:
        """验证模型名称"""
        return self.model.startswith(('deepseek-', 'deepseek_chat'))


class DashScopeClient(BaseLLMClient):
    """阿里云 DashScope (Qwen) 客户端"""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        if not DASHSCOPE_AVAILABLE:
            raise ImportError("dashscope SDK 未安装。请运行: pip install dashscope")

        super().__init__(model, base_url, **kwargs)

        # 温度参数检查
        assert kwargs.get('temperature', 0.0) == 0.0, "temperature 必须为 0.0"

        api_key = kwargs.get('api_key', '')
        dashscope.api_key = api_key

    def get_llm(self) -> Any:
        """返回 DashScope Qwen 实例（temperature=0.0）"""
        return dashscope.Generation.call(
            model=self.model,
            temperature=0.0,  # 硬编码为 0.0
            **{k: v for k, v in self.kwargs.items() if k not in ['temperature']}
        )

    def validate_model(self) -> bool:
        """验证模型名称"""
        return self.model.startswith(('qwen-', 'qwen-turbo', 'qwen-plus'))


class LLMFactory:
    """
    LLM 工厂类

    扩展原版 LLM 工厂，支持更多提供商。
    所有适配器的 temperature 参数必须硬编码为 0.0
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def create(
        self,
        provider: str,
        model: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> BaseLLMClient:
        """
        创建 LLM 客户端实例

        Args:
            provider: 提供商名称 (openai, anthropic, google, deepseek, dashscope, ollama)
            model: 模型名称
            base_url: API 端点 URL
            **kwargs: 额外参数

        Returns:
            BaseLLMClient 实例

        Raises:
            ValueError: 提供商不支持
        """
        provider_lower = provider.lower()

        # OpenAI 兼容客户端（OpenAI, Ollama, XAI, OpenRouter）
        if provider_lower in ("openai", "ollama", "xai", "openrouter"):
            return OpenAIClient(model, base_url, provider=provider_lower, **kwargs)

        # Anthropic Claude
        if provider_lower == "anthropic":
            return AnthropicClient(model, base_url, **kwargs)

        # Google Gemini
        if provider_lower == "google":
            return GoogleClient(model, base_url, **kwargs)

        # DeepSeek
        if provider_lower == "deepseek":
            return DeepSeekClient(model, base_url, **kwargs)

        # DashScope (阿里云 Qwen)
        if provider_lower == "dashscope":
            return DashScopeClient(model, base_url, **kwargs)

        raise ValueError(f"不支持的 LLM 提供商: {provider}")

    def create_mock(self) -> Any:
        """创建 Mock LLM 用于测试"""
        # 简单 Mock，实际可以使用 unittest.mock
        return None


# 模块级便捷函数
def create_llm(
    provider: str,
    model: str,
    base_url: Optional[str] = None,
    **kwargs
) -> BaseLLMClient:
    """
    便捷函数：创建 LLM 客户端

    Args:
        provider: 提供商名称
        model: 模型名称
        base_url: API 端点 URL
        **kwargs: 额外参数

    Returns:
        BaseLLMClient 实例
    """
    factory = LLMFactory()
    return factory.create(provider, model, base_url, **kwargs)
