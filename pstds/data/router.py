# pstds/data/router.py
# 市场路由器 - 集成 FallbackManager

import re
from typing import Literal, List, Optional
from pstds.data.models import MarketType
from pstds.temporal.context import TemporalContext
from pstds.data.fallback import DataQualityReport


class MarketNotSupportedError(ValueError):
    """市场不支持错误 (错误码 E009)"""

    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"股票代码格式无法识别: {symbol} (错误码: E009)")


class MarketRouter:
    """
    市场路由器

    根据股票代码格式自动识别市场类型：
    - A股: 6位数字，首2位在 {60,00,30,68,83,43}
    - 港股: 4-5位数字 + .HK 后缀
    - 美股: 1-5位字母
    """

    # A股首2位代码范围
    CN_A_PREFIXES = {"60", "00", "30", "68", "83", "43"}

    @staticmethod
    def route(symbol: str) -> MarketType:
        """
        根据股票代码路由到市场类型

        Args:
            symbol: 股票代码

        Returns:
            市场类型: "US", "CN_A", 或 "HK"

        Raises:
            MarketNotSupportedError: 当股票代码格式无法识别时抛出
        """
        # 港股: ^\d{4,5}\.HK$
        if re.match(r"^\d{4,5}\.HK$", symbol):
            return "HK"

        # A股: ^[0-9]{6}$ 且首2位在 CN_A_PREFIXES
        if re.match(r"^[0-9]{6}$", symbol):
            prefix = symbol[:2]
            if prefix in MarketRouter.CN_A_PREFIXES:
                return "CN_A"

        # 美股: ^[A-Za-z]{1,5}$ 或 ^[A-Za-z]{1,4}\.[A-Za-z0-9]{1}$ (如 BRK.B)
        if re.match(r"^[A-Za-z]{1,5}$", symbol) or re.match(r"^[A-Za-z]{1,4}\.[A-Za-z0-9]{1}$", symbol):
            return "US"

        # 无法识别
        raise MarketNotSupportedError(symbol)


class DataRouter:
    """
    数据路由器 - 集成 FallbackManager

    根据股票代码和市场类型返回主源适配器（附带自动降级能力）
    """

    def __init__(self, config: dict = None):
        """
        初始化数据路由器

        Args:
            config: 配置字典，包含数据源配置
        """
        self.config = config or {}

        # 延迟导入适配器（避免循环依赖）
        from pstds.data.adapters.yfinance_adapter import YFinanceAdapter
        from pstds.data.adapters.akshare_adapter import AKShareAdapter
        from pstds.data.adapters.local_csv_adapter import LocalCSVAdapter
        from pstds.fallback import FallbackManager

        # 初始化适配器实例
        self.yfinance_adapter = YFinanceAdapter()
        self.akshare_adapter = AKShareAdapter()
        self.local_adapter = LocalCSVAdapter()

        # 市场到适配器的映射（主源）
        self.market_adapters = {
            "US": self.yfinance_adapter,
            "CN_A": self.akshare_adapter,
            "HK": self.akshare_adapter,  # 港股主源为 AKShare，备用为 YFinance
        }

    def get_market_type(self, symbol: str) -> MarketType:
        """
        获取股票对应的市场类型

        Args:
            symbol: 股票代码

        Returns:
            市场类型: "US", "CN_A", 或 "HK"
        """
        return MarketRouter.route(symbol)

    def get_adapter(
        self,
        symbol: str,
        ctx: Optional[TemporalContext] = None,
        quality_report: Optional[DataQualityReport] = None,
    ) -> any:
        """
        获取主源适配器（附带自动降级能力）

        Args:
            symbol: 股票代码
            ctx: 时间上下文（可选）
            quality_report: 数据质量报告（可选）

        Returns:
            适配器实例
        """
        market_type = self.get_market_type(symbol)

        # 返回主源适配器
        return self.market_adapters.get(market_type, self.yfinance_adapter)

    def get_fallback_manager(
        self,
        symbol: str,
        quality_report: Optional[DataQualityReport] = None,
    ) -> any:
        """
        获取带回退能力的适配器管理器

        Args:
            symbol: 股票代码
            quality_report: 数据质量报告（可选）

        Returns:
            FallbackManager 实例
        """
        from pstds.fallback import FallbackManager

        market_type = self.get_market_type(symbol)

        # 根据市场类型配置主源和备用源
        if market_type == "US":
            primary_adapters = [self.yfinance_adapter]
            fallback_adapters = [self.local_adapter]
        elif market_type == "CN_A":
            primary_adapters = [self.akshare_adapter]
            fallback_adapters = [self.local_adapter]
        elif market_type == "HK":
            primary_adapters = [self.akshare_adapter]
            fallback_adapters = [self.yfinance_adapter, self.local_adapter]
        else:
            primary_adapters = [self.yfinance_adapter]
            fallback_adapters = [self.local_adapter]

        return FallbackManager(
            primary_adapters=primary_adapters,
            fallback_adapters=fallback_adapters,
            report=quality_report
        )
