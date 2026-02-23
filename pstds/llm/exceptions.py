# pstds/llm/exceptions.py
# LLM 模块异常定义 - ISD v2.0 Section 4.4
# 错误码对应文档: E006 = LLMRateLimitError, E010 = ConfigurationError


class LLMError(Exception):
    """LLM 基础异常"""
    pass


class ConfigurationError(LLMError):
    """
    配置错误 (E010)

    API Key 未设置或配置无效时抛出。
    """
    code = "E010"


class LLMRateLimitError(LLMError):
    """
    速率限制错误 (E006)

    API 返回 429 且重试耗尽后抛出。
    """
    code = "E006"
