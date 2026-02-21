# pstds/data/adapters/akshare_adapter.py
# AKShare 数据适配器 - ISD v1.0 Section 4.1

import akshare as ak
import pandas as pd
from typing import List, Literal
from datetime import date, datetime

from pstds.temporal.context import TemporalContext
from pstds.temporal.guard import TemporalGuard, RealtimeAPIBlockedError
from pstds.data.adapters.base import MarketDataAdapter
from pstds.data.models import NewsItem, MarketType


class AKShareAdapter:
    """
    AKShare 数据适配器

    主要用于 A 股和港股数据获取。
    """

    def __init__(self):
        self.name = "akshare"

    # A股财务字段中文→英文映射
    _FUNDAMENTALS_MAP = {
        "市盈率": "pe_ratio",
        "市净率": "pb_ratio",
        "净资产收益率": "roe",
        "营业收入": "revenue",
        "净利润": "net_income",
        "公告日期": "earnings_date",
        "报告期": "report_period",
    }

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
        """
        # 时间隔离校验
        TemporalGuard.validate_timestamp(end_date, ctx, f"{self.name}.get_ohlcv")

        try:
            if symbol.endswith(".HK"):
                # 港股接口
                hk_code = symbol.replace(".HK", "")
                df = ak.stock_hk_hist(
                    symbol=hk_code,
                    period="daily",
                    adjust="qfq"  # 前复权
                )
            else:
                # A股接口
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    adjust="qfq",  # 前复权
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d")
                )

            if df.empty:
                return pd.DataFrame(columns=[
                    "date", "open", "high", "low", "close",
                    "volume", "adj_close", "data_source"
                ])

            # 标准化列名
            column_map = {
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "涨跌幅": "change_pct"
            }
            df = df.rename(columns=column_map)

            # 确保 date 列为 datetime
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], utc=True)

            # AKShare 没有复权价，使用收盘价
            df["adj_close"] = df["close"]

            # 添加 data_source 和 fetched_at
            df["data_source"] = self.name
            df["fetched_at"] = datetime.utcnow()

            # 确保列名和顺序
            required_cols = ["date", "open", "high", "low", "close", "volume", "adj_close", "data_source"]
            existing_cols = [c for c in required_cols if c in df.columns]
            df = df[existing_cols]

            return df

        except Exception as e:
            print(f"AKShareAdapter.get_ohlcv error: {e}")
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

        A股财务字段中文→英文映射
        """
        try:
            # BACKTEST 模式禁止调用实时 API
            TemporalGuard.assert_backtest_safe(ctx, f"{self.name}.get_fundamentals")

            if symbol.endswith(".HK"):
                # 港股基本面数据
                df = ak.stock_hk_spot_em()
                if df.empty:
                    raise ValueError("港股基本面数据不可用")
            else:
                # A股基本面数据
                df = ak.stock_individual_info_em(symbol=symbol)

            # 映射中文字段到英文
            result = {}
            for cn_key, en_key in self._FUNDAMENTALS_MAP.items():
                value = None
                if cn_key in df.columns:
                    value = df[cn_key].iloc[0] if not df.empty else None
                elif not df.empty and en_key in ["revenue", "net_income"]:
                    # 尝试从其他字段获取
                    if en_key == "revenue" and "营业收入" in df.columns:
                        value = df["营业收入"].iloc[0]
                    elif en_key == "net_income" and "净利润" in df.columns:
                        value = df["净利润"].iloc[0]

                result[en_key] = value

            result["data_source"] = self.name
            result["fetched_at"] = datetime.utcnow()

            return result

        except Exception as e:
            print(f"AKShareAdapter.get_fundamentals error: {e}")
            return {
                "pe_ratio": None,
                "pb_ratio": None,
                "roe": None,
                "revenue": None,
                "net_income": None,
                "earnings_date": None,
                "report_period": None,
                "data_source": self.name,
                "fetched_at": datetime.utcnow(),
            }

    def get_news(
        self,
        symbol: str,
        days_back: int,
        ctx: TemporalContext,
    ) -> List[NewsItem]:
        """
        获取新闻数据

        东方财富股吧情绪数据标准化为 NewsItem 格式
        """
        try:
            # BACKTEST 模式禁止调用实时 API
            TemporalGuard.assert_backtest_safe(ctx, f"{self.name}.get_news")

            # 东方财富股吧情绪数据
            df = ak.stock_comment_em(symbol=symbol)

            if df.empty:
                return []

            # 转换为 NewsItem 格式
            news_items = []
            for _, row in df.iterrows():
                # 情绪内容作为 content
                content = str(row.get("评论内容", ""))[:500]

                # 时间戳处理
                published_at = datetime.utcnow()  # 默认值
                if "发布时间" in row:
                    try:
                        published_at = pd.to_datetime(row["发布时间"])
                    except:
                        pass

                news_items.append(NewsItem(
                    title=row.get("评论用户", "用户评论"),
                    content=content,
                    published_at=published_at,
                    source="东方财富股吧",
                    url=None,
                    relevance_score=0.65,  # 默认中等相关性
                    market_type="CN_A" if not symbol.endswith(".HK") else "HK",
                    symbol=symbol,
                ))

            # 过滤未来新闻
            filtered = TemporalGuard.filter_news(news_items, ctx)

            return filtered

        except Exception as e:
            print(f"AKShareAdapter.get_news error: {e}")
            return []

    def is_available(self, symbol: str) -> bool:
        """检查数据源是否支持该股票代码"""
        try:
            if symbol.endswith(".HK"):
                # 港股检查
                df = ak.stock_hk_spot_em()
                return not df.empty
            else:
                # A股检查
                df = ak.stock_individual_info_em(symbol=symbol)
                return not df.empty
        except:
            return False

    def get_market_type(self, symbol: str) -> Literal["US", "CN_A", "HK"]:
        """获取股票对应的市场类型"""
        if symbol.endswith(".HK"):
            return "HK"
        elif symbol.isdigit() and len(symbol) == 6:
            return "CN_A"
        else:
            return "CN_A"  # 默认为 A股
