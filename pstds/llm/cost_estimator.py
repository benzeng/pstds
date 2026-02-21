# pstds/llm/cost_estimator.py
# Token 成本估算与核算 - Phase 3 Task 2

from typing import Dict, Optional


class CostEstimator:
    """
    Token 成本估算器

    提供预估和实际核算功能，价格表硬编码主流模型。
    可定期更新价格表。
    """

    # 主流模型价格表（每百万 token 价格，USD）
    _PRICE_TABLE = {
        # OpenAI
        "gpt-4o": 5.00,
        "gpt-4o-mini": 0.15,
        "gpt-4-turbo": 0.50,
        "gpt-3.5-turbo": 0.50,
        # Anthropic Claude
        "claude-3-opus-20240229": 15.00,
        "claude-3-sonnet-20240229": 3.00,
        "claude-3-haiku-20240307": 0.25,
        "claude-3-5-sonnet-20241022": 3.00,
        "claude-3-5-haiku-20241022": 0.10,
        # Google Gemini
        "gemini-1.5-pro": 3.50,
        "gemini-1.5-flash": 0.075,
        "gemini-1.0-pro": 3.50,
        # DeepSeek
        "deepseek-chat": 0.14,
        "deepseek-coder": 0.14,
        # DashScope (阿里云 Qwen)
        "qwen-turbo": 0.30,
        "qwen-plus": 0.40,
        "qwen-max": 1.20,
        "qwen2-72b-chat": 0.10,
        # 通用默认价格
        "default": 0.10,
    }

    @classmethod
    def estimate(
        cls,
        prompt: str,
        model: str,
    ) -> Dict[str, any]:
        """
        预估阶段（按每 4 字符 ≈ 1 token 估算）

        Args:
            prompt: 提示词字符串
            model: 模型名称

        Returns:
            包含以下字段的字典：
            - estimated_tokens: 估算的 token 数量
            - estimated_cost_usd: 估算成本（USD）
            - model: 模型名称
            - price_per_million: 每百万 token 价格
        """
        # 估算 token 数量（简化：每 4 字符 ≈ 1 token）
        estimated_tokens = len(prompt) // 4

        # 获取模型价格
        price_per_million = cls._PRICE_TABLE.get(model, cls._PRICE_TABLE["default"])

        # 计算预估成本
        estimated_cost = (estimated_tokens / 1_000_000) * price_per_million

        return {
            "estimated_tokens": estimated_tokens,
            "estimated_cost_usd": estimated_cost,
            "model": model,
            "price_per_million": price_per_million,
        }

    @classmethod
    def record_actual(
        cls,
        usage: Dict[str, int],
        model: str,
    ) -> Dict[str, any]:
        """
        核算阶段（从 API 响应 usage 字段提取）

        Args:
            usage: API 响应中的 usage 字段，包含：
                - prompt_tokens: 输入 token 数量
                - completion_tokens: 输出 token 数量
                - total_tokens: 总 token 数量
            model: 模型名称

        Returns:
            包含以下字段的字典：
            - prompt_tokens: 输入 token 数量
            - completion_tokens: 输出 token 数量
            - total_tokens: 总 token 数量
            - actual_cost_usd: 实际成本（USD）
            - model: 模型名称
            - price_per_million: 每百万 token 价格
        """
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        # 获取模型价格
        price_per_million = cls._PRICE_TABLE.get(model, cls._PRICE_TABLE["default"])

        # 计算实际成本
        actual_cost = (total_tokens / 1_000_000) * price_per_million

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "actual_cost_usd": actual_cost,
            "model": model,
            "price_per_million": price_per_million,
        }

    @classmethod
    def get_model_price(cls, model: str) -> Optional[float]:
        """
        获取模型价格

        Args:
            model: 模型名称

        Returns:
            每百万 token 价格（USD），如果模型未找到则返回 None
        """
        return cls._PRICE_TABLE.get(model)

    @classmethod
    def update_price(cls, model: str, price: float) -> None:
        """
        更新模型价格（可用于运行时更新价格）

        Args:
            model: 模型名称
            price: 新价格（每百万 token，USD）
        """
        cls._PRICE_TABLE[model] = price

    @classmethod
    def get_all_prices(cls) -> Dict[str, float]:
        """获取所有模型价格表"""
        return cls._PRICE_TABLE.copy()
