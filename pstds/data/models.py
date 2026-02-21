# pstds/data/models.py
# 数据模型定义 - ISD v1.0 Section 2.1, 2.3, 2.4

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime


# ─── 类型别名 ────────────────────────────────────────────
MarketType = Literal["US", "CN_A", "HK"]
ActionType = Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL", "INSUFFICIENT_DATA"]
ConvictionLevel = Literal["HIGH", "MEDIUM", "LOW"]
DepthLevel = Literal["L0", "L1", "L2", "L3"]
AnalysisMode = Literal["LIVE", "BACKTEST"]


# ─── NewsItem (ISD v1.0 Section 2.3) ────────────────────────────
class NewsItem(BaseModel):
    """新闻数据项"""

    title: str  # 新闻标题

    content: str  # 新闻正文（截断至 500 tokens）

    published_at: datetime  # 发布时间（UTC）

    source: str  # 来源名称

    url: Optional[str] = None  # 原始链接

    relevance_score: float  # 相关性评分 0.0-1.0

    market_type: MarketType

    symbol: str

    @field_validator("relevance_score")
    @classmethod
    def score_must_be_valid(cls, v: float) -> float:
        """relevance_score 必须在 0-1 之间"""
        if not (0.0 <= v <= 1.0):
            raise ValueError("relevance_score 必须在 0-1 之间")
        return v

    # 注意：TemporalGuard 会在返回前过滤 published_at > analysis_date 的项目


# ─── OHLCVRecord (ISD v1.0 Section 2.4) ───────────────────────────
class OHLCVRecord(BaseModel):
    """行情数据"""

    symbol: str

    date: datetime  # UTC datetime

    open: float = Field(gt=0)

    high: float = Field(gt=0)

    low: float = Field(gt=0)

    close: float = Field(gt=0)

    volume: int = Field(ge=0)

    adj_close: Optional[float] = None

    data_source: str  # "yfinance"|"akshare"|"alphavantage"|"local"

    fetched_at: datetime  # 数据获取时间（UTC）

    @model_validator(mode="after")
    def validate_high_low(self) -> "OHLCVRecord":
        """high 必须 >= low"""
        if self.high < self.low:
            raise ValueError("high 必须 >= low")
        return self
