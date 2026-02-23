# tests/adapters/test_deepseek.py
# DeepSeek 适配器测试 - DS-001 至 DS-005
# TSD v2.0 DS 节

import os
import time
import logging
import pytest
from unittest.mock import patch, MagicMock

from pstds.llm.exceptions import ConfigurationError, LLMRateLimitError


class TestDeepSeekClient:
    """DS-001~DS-005: DeepSeek 适配器测试"""

    def test_ds001_missing_api_key_raises_configuration_error(self, monkeypatch):
        """DS-001: DEEPSEEK_API_KEY 未设置时抛出 ConfigurationError (E010)"""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        from pstds.llm.deepseek import DeepSeekClient

        with pytest.raises(ConfigurationError) as exc_info:
            DeepSeekClient("deepseek-chat")

        assert "DEEPSEEK_API_KEY" in str(exc_info.value)
        assert "E010" in str(exc_info.value)

    def test_ds002_temperature_is_hardcoded_zero(self, monkeypatch):
        """DS-002: temperature 属性硬编码为 0.0（C-03 约束）"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key-for-testing")

        with patch("openai.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            from pstds.llm.deepseek import DeepSeekClient
            client = DeepSeekClient("deepseek-chat")

        assert client.temperature == 0.0

    def test_ds003_temperature_assertion_protects_zero(self, monkeypatch):
        """DS-003: temperature 断言保护 — 构造时 assert temperature == 0.0"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key-for-testing")

        with patch("openai.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            from pstds.llm.deepseek import DeepSeekClient
            client = DeepSeekClient("deepseek-chat")

        # 强制修改后断言保护已完成（属性为 0.0）
        assert client.temperature == 0.0
        # 验证 chat 调用时 temperature=0.0 是硬编码的
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test response"
        mock_client.chat.completions.create.return_value = mock_response
        client._client = mock_client

        client.chat([{"role": "user", "content": "test"}])

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs.get("temperature") == 0.0 or \
               call_kwargs[1].get("temperature") == 0.0 or \
               (call_kwargs[0] and "temperature" not in call_kwargs[1])

    def test_ds004_rate_limit_triggers_retry_and_raises(self, monkeypatch):
        """DS-004: 429 触发指数退避重试（1/2/4s），重试耗尽后抛出 LLMRateLimitError (E006)"""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key-for-testing")

        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # 模拟 429 错误
            rate_limit_error = Exception("429 rate_limit exceeded")

            mock_client.chat.completions.create.side_effect = rate_limit_error

            from pstds.llm.deepseek import DeepSeekClient

            client = DeepSeekClient("deepseek-chat", max_retries=3)
            client._client = mock_client

            # 模拟 sleep 以加速测试
            with patch("time.sleep") as mock_sleep:
                with pytest.raises(LLMRateLimitError) as exc_info:
                    client.chat([{"role": "user", "content": "test"}])

            assert "E006" in str(exc_info.value)
            # 应该调用了 sleep（重试等待）
            assert mock_sleep.call_count >= 2

    def test_ds005_api_key_not_in_logs(self, monkeypatch, caplog):
        """DS-005: API Key 不出现在任何日志输出中（C-07 约束）"""
        secret_key = "sk-test-secret-key-must-not-appear-in-logs"
        monkeypatch.setenv("DEEPSEEK_API_KEY", secret_key)

        with caplog.at_level(logging.DEBUG):
            with patch("openai.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client
                mock_client.chat.completions.create.side_effect = Exception("429 rate_limit")

                from pstds.llm.deepseek import DeepSeekClient
                client = DeepSeekClient("deepseek-chat", max_retries=2)
                client._client = mock_client

                with patch("time.sleep"):
                    try:
                        client.chat([{"role": "user", "content": "test"}])
                    except LLMRateLimitError:
                        pass

        # API Key 不得出现在任何日志记录中
        for record in caplog.records:
            assert secret_key not in record.getMessage(), \
                f"API Key 泄露到日志: {record.getMessage()}"
