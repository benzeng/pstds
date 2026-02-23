# pstds/llm/dashscope.py
# DashScope (阿里云 Qwen) LLM 适配器 - ISD v2.0 Section 4.4
# Phase 1 Task 3 (P1-T3)

import os
import time
import logging
from typing import Dict, List

from pstds.llm.exceptions import ConfigurationError, LLMRateLimitError

logger = logging.getLogger(__name__)

DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
_RETRY_DELAYS = [1, 2, 4]


class DashScopeClient:
    """
    DashScope (阿里云 Qwen) LLM 适配器 - ISD v2.0 Section 4.4

    使用 openai 包兼容 DashScope API（OpenAI 兼容模式）。
    - API Key 从 DASHSCOPE_API_KEY 环境变量读取（C-07）
    - temperature 硬编码 0.0，断言保护（C-03）
    - 429 → 指数退避 1/2/4s，最多 3 次 → LLMRateLimitError（E006）
    """

    def __init__(self, model: str, base_url: str = DASHSCOPE_BASE_URL, max_retries: int = 3):
        self.model = model
        self.base_url = base_url
        self.max_retries = max_retries

        # C-03
        self.temperature = 0.0
        assert self.temperature == 0.0, "temperature 必须为 0.0"

        # C-07：从环境变量读取，不打印
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            raise ConfigurationError("DASHSCOPE_API_KEY 环境变量未设置 (E010)")

        import openai
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        调用 DashScope chat API，temperature 强制 0.0。

        Raises:
            LLMRateLimitError: 429 且重试耗尽（E006）
        """
        kwargs.pop("temperature", None)
        last_error = None

        for attempt in range(self.max_retries):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.0,
                    **kwargs,
                )
                return resp.choices[0].message.content
            except Exception as e:
                s = str(e)
                if "429" in s or "rate_limit" in s.lower() or "RateLimitError" in type(e).__name__:
                    last_error = e
                    if attempt < len(_RETRY_DELAYS):
                        delay = _RETRY_DELAYS[attempt]
                        logger.warning(f"[DashScope] 429 速率限制，{delay}s 后重试（第{attempt+1}次）")
                        time.sleep(delay)
                    continue
                raise

        raise LLMRateLimitError(
            f"DashScope API 速率限制，{self.max_retries} 次重试耗尽 (E006): {last_error}"
        )

    def get_model(self) -> str:
        return self.model
