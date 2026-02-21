# pstds/data/adapters/local_csv_adapter.py
# Local CSV 数据适配器 - ISD v1.0 Section 4.1

import pandas as pd
from typing import List, Literal
from datetime import date, datetime
from pathlib import Path

from pstds.temporal.context import TemporalContext
from pstds.temporal.guard import TemporalGuard
from pstds.data.adapters.base import MarketDataAdapter
from pstds.data.models import NewsItem


class LocalCSVAdapter:
    """
    Local CSV 数据适配器

    读取本地 CSV 文件，天然时间隔离（过滤 date > analysis_date 的行）。
    用于回测场景，确保数据不可篡改。
    """

    def __init__(self, data_dir: str = "./data/raw/prices"):
        self.name = "local_csv"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

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

        读取 data/raw/prices/{symbol}.csv
        天然时间隔离：过滤 date > ctx.analysis_date 的行
        """
        csv_path = self.data_dir / f"{symbol}.csv"

        if not csv_path.exists():
            print(f"LocalCSVAdapter: CSV file not found: {csv_path}")
            return pd.DataFrame(columns=[
                "date", "open", "high", "low", "close",
                "volume", "adj_close", "data_source"
            ])

        try:
            df = pd.read_csv(csv_path)

            # 确保 date 列为 datetime
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], utc=True)

            # 天然时间隔离：过滤 date > analysis_date 的行
            analysis_date = ctx.analysis_date
            df = df[df["date"].dt.date <= analysis_date]

            # 进一步按日期范围过滤
            if "date" in df.columns:
                start_dt = pd.Timestamp(start_date, tz="UTC")
                end_dt = pd.Timestamp(end_date, tz="UTC")
                df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]

            if df.empty:
                return pd.DataFrame(columns=[
                    "date", "open", "high", "low", "close",
                    "volume", "adj_close", "data_source"
                ])

            # 添加 data_source
            df["data_source"] = self.name

            # 确保列名和顺序
            required_cols = ["date", "open", "high", "low", "close", "volume", "adj_close", "data_source"]
            existing_cols = [c for c in required_cols if c in df.columns]
            df = df[existing_cols]

            return df

        except Exception as e:
            print(f"LocalCSVAdapter.get_ohlcv error: {e}")
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

        本地 CSV 不支持基本面数据，返回 None 值字典
        """
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

        本地 CSV 不支持新闻数据，返回空列表
        """
        return []

    def is_available(self, symbol: str) -> bool:
        """检查 CSV 文件是否存在"""
        csv_path = self.data_dir / f"{symbol}.csv"
        return csv_path.exists()

    def get_market_type(self, symbol: str) -> Literal["US", "CN_A", "HK"]:
        """获取股票对应的市场类型"""
        if symbol.endswith(".HK"):
            return "HK"
        elif symbol.isdigit() and len(symbol) == 6:
            return "CN_A"
        else:
            return "US"
