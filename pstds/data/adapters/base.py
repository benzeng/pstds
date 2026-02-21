# pstds/data/adapters/base.py
# MarketDataAdapter Protocol - ISD v1.0 Section 4

from typing import Protocol, List, Literal
from datetime import date
import pandas as pd

from pstds.temporal.context import TemporalContext
from pstds.data.models import NewsItem


class MarketDataAdapter(Protocol):
    """
    市场数据适配器协议

    所有数据适配器必须实现此接口，确保方法签名一致。
    TemporalContext 为必传参数，不可省略。
    """

    def get_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: Literal["1d", "1wk", "1mo"],
        ctx: TemporalContext,  # 必填，时间隔离上下文
    ) -> pd.DataFrame:
        """
        获取 OHLCV 行情数据

        Args:
            symbol: 股票代码
            start_date: 起始日期
            end_date: 结束日期
            interval: K线周期：1d日线, 1w周线, 1mo月线
            ctx: 时间上下文（必填）

        Returns:
            标准化 DataFrame，列名固定：
            ['date', 'open', 'high', 'low', 'close', 'volume', 'adj_close', 'data_source']
            - date 列：UTC datetime
            - 内部调用 TemporalGuard.validate_timestamp(end_date, ctx)
        """
        ...

    def get_fundamentals(
        self,
        symbol: str,
        as_of_date: date,  # 返回该日期可用的最新财报
        ctx: TemporalContext,
    ) -> dict:
        """
        获取基本面数据

        Args:
            symbol: 股票代码
            as_of_date: 返回该日期可用的最新财报
            ctx: 时间上下文（必填）

        Returns:
            必含字段：pe_ratio, pb_ratio, roe, revenue, net_income,
            earnings_date, report_period, data_source, fetched_at
            缺失字段用 None 填充，不得抛出异常
        """
        ...

    def get_news(
        self,
        symbol: str,
        days_back: int,
        ctx: TemporalContext,
    ) -> List[NewsItem]:
        """
        获取新闻数据

        Args:
            symbol: 股票代码
            days_back: 向前查询的天数
            ctx: 时间上下文（必填）

        Returns:
            返回的 NewsItem 列表已通过时间隔离校验
            内部调用 TemporalGuard.filter_news() 过滤未来新闻
            relevance_score < 0.6 的项目在内部过滤
        """
        ...

    def is_available(self, symbol: str) -> bool:
        """
        检查数据源是否支持该股票代码

        Args:
            symbol: 股票代码

        Returns:
            True 表示支持，False 表示不支持
        """
        ...

    def get_market_type(self, symbol: str) -> Literal["US", "CN_A", "HK"]:
        """
        获取股票对应的市场类型

        Args:
            symbol: 股票代码

        Returns:
            市场类型: "US", "CN_A", 或 "HK"
        """
        ...
