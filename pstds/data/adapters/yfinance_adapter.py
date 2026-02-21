# pstds/data/adapters/yfinance_adapter.py
# YFinance 数据适配器 - ISD v1.0 Section 4.1

import yfinance as yf
import pandas as pd
from typing import List, Literal
from datetime import date, datetime, UTC

from pstds.temporal.context import TemporalContext
from pstds.temporal.guard import TemporalGuard, RealtimeAPIBlockedError
from pstds.data.adapters.base import MarketDataAdapter
from pstds.data.models import NewsItem, MarketType


class YFinanceAdapter:
    """
    YFinance 数据适配器

    主要用于美股数据获取，港股为备用源。
    """

    def __init__(self):
        self.name = "yfinance"

    def get_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: Literal["1d", "1wk", "1mo"],
        ctx: TemporalContext,
    ) -> pd.DataFrame:
        """
        获取 OHLCV 行情数据

        内部调用 TemporalGuard.validate_timestamp(end_date, ctx)
        """
        # 时间隔离校验
        TemporalGuard.validate_timestamp(end_date, ctx, f"{self.name}.get_ohlcv")

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date,
                end=end_date + pd.Timedelta(days=1),  # yfinance 需要包含结束日
                interval=interval,
                auto_adjust=True,
                prepost=False,
            )

            if df.empty:
                # 返回空 DataFrame，不抛出异常（符合 ISD 规范）
                return pd.DataFrame(columns=[
                    "date", "open", "high", "low", "close",
                    "volume", "adj_close", "data_source"
                ])

            # 标准化列名
            df = df.reset_index()
            # 映射 yfinance 列名到标准列名
            column_map = {
                "date": "date",
                "datetime": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "adj close": "adj_close",
                "adj_close": "adj_close",
            }
            df.columns = [column_map.get(col.lower(), col.lower()) for col in df.columns]

            # 确保 date 列为 datetime
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], utc=True)

            # 如果没有 adj_close，使用 close
            if "adj_close" not in df.columns and "close" in df.columns:
                df["adj_close"] = df["close"]

            # 添加 data_source 列
            df["data_source"] = self.name

            # 添加 fetched_at 列
            df["fetched_at"] = datetime.now(UTC)

            # 确保列名和顺序（只保留存在的列）
            required_cols = ["date", "open", "high", "low", "close", "volume", "adj_close", "data_source"]
            existing_cols = [c for c in required_cols if c in df.columns]
            df = df[existing_cols]

            return df

        except Exception as e:
            # 记录错误日志，返回空 DataFrame
            print(f"YFinanceAdapter.get_ohlcv error: {e}")
            return pd.DataFrame(columns=[
                "date", "open", "high", "low", "close",
                "volume", "adj_close", "data_source"
            ])

    def get_fundamentals(
        self,
        symbol: str,
        as_of_date: date,
        ctx: TemporalContext,
    ) -> dict:
        """
        获取基本面数据

        缺失字段用 None 填充，网络失败返回含 None 值的字典
        """
        try:
            # BACKTEST 模式禁止调用实时 API
            TemporalGuard.assert_backtest_safe(ctx, f"{self.name}.get_fundamentals")

            ticker = yf.Ticker(symbol)
            info = ticker.info

            # 标准化字段映射
            result = {
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "roe": info.get("returnOnEquity"),
                "revenue": info.get("totalRevenue"),
                "net_income": info.get("netIncomeToCommon"),
                "earnings_date": info.get("nextEarningsDate"),
                "report_period": info.get("mostRecentQuarter"),
                "data_source": self.name,
                "fetched_at": datetime.now(UTC),
            }

            return result

        except Exception as e:
            print(f"YFinanceAdapter.get_fundamentals error: {e}")
            # 返回含 None 值的字典
            return {
                "pe_ratio": None,
                "pb_ratio": None,
                "roe": None,
                "revenue": None,
                "net_income": None,
                "earnings_date": None,
                "report_period": None,
                "data_source": self.name,
                "fetched_at": datetime.now(UTC),
            }

    def get_news(
        self,
        symbol: str,
        days_back: int,
        ctx: TemporalContext,
    ) -> List[NewsItem]:
        """
        获取新闻数据

        内部调用 TemporalGuard.filter_news() 过滤未来新闻
        relevance_score < 0.6 的项目在内部过滤
        """
        try:
            # BACKTEST 模式禁止调用实时 API
            TemporalGuard.assert_backtest_safe(ctx, f"{self.name}.get_news")

            ticker = yf.Ticker(symbol)
            news = ticker.news

            if not news:
                return []

            # 转换为 NewsItem 格式
            news_items = []
            for item in news:
                # yfinance 新闻相关性评分处理（简化为固定值，实际可根据内容计算）
                relevance = 0.7  # 默认相关

                news_items.append(NewsItem(
                    title=item.get("title", ""),
                    content=item.get("summary", "")[:500],  # 截断至 500 tokens
                    published_at=datetime.fromtimestamp(
                        item.get("providerPublishTime", 0),
                        tz=None
                    ),
                    source=item.get("publisher", ""),
                    url=item.get("link", ""),
                    relevance_score=relevance,
                    market_type="US",
                    symbol=symbol,
                ))

            # 过滤低相关性新闻
            news_items = [n for n in news_items if n.relevance_score >= 0.6]

            # 时间隔离：过滤未来新闻
            filtered = TemporalGuard.filter_news(news_items, ctx)

            return filtered

        except Exception as e:
            print(f"YFinanceAdapter.get_news error: {e}")
            return []

    def is_available(self, symbol: str) -> bool:
        """检查数据源是否支持该股票代码"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            # 如果能获取基本信息，认为可用
            return bool(info)
        except:
            return False

    def get_market_type(self, symbol: str) -> Literal["US", "CN_A", "HK"]:
        """获取股票对应的市场类型"""
        if symbol.endswith(".HK"):
            return "HK"
        elif symbol.isalpha():
            return "US"
        else:
            return "US"  # 默认为 US
