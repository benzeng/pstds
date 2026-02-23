# tests/adapters/test_dashscope.py
# DashScope 适配器测试 - QW-001 至 QW-003
# TSD v2.0 QW 节

import os
import logging
import pytest
from unittest.mock import patch, MagicMock

from pstds.llm.exceptions import ConfigurationError, LLMRateLimitError


class TestDashScopeClient:
    """QW-001~QW-003: DashScope (Qwen) 适配器测试"""

    def test_qw001_missing_api_key_raises_configuration_error(self, monkeypatch):
        """QW-001: DASHSCOPE_API_KEY 未设置时抛出 ConfigurationError (E010)"""
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

        from pstds.llm.dashscope import DashScopeClient

        with pytest.raises(ConfigurationError) as exc_info:
            DashScopeClient("qwen-max")

        assert "DASHSCOPE_API_KEY" in str(exc_info.value)
        assert "E010" in str(exc_info.value)

    def test_qw002_temperature_is_hardcoded_zero(self, monkeypatch):
        """QW-002: temperature 属性硬编码为 0.0（C-03 约束）"""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-qwen-key")

        with patch("openai.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            from pstds.llm.dashscope import DashScopeClient
            client = DashScopeClient("qwen-max")

        assert client.temperature == 0.0

    def test_qw003_llm_factory_cn_a_returns_dashscope(self, monkeypatch):
        """QW-003: LLMFactory.create(market_type="CN_A") 返回 DashScopeClient("qwen-max")"""
        monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-qwen-key")

        with patch("openai.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()

            from pstds.llm.factory import LLMFactory
            from pstds.llm.dashscope import DashScopeClient

            factory = LLMFactory()
            client = factory.create(market_type="CN_A")

        assert isinstance(client, DashScopeClient), \
            f"期望 DashScopeClient，实际得到 {type(client).__name__}"
        assert client.model == "qwen-max"
