# pstds/agents/output_schemas.py
# ISD v1.0 Section 3: TradeDecision 标准决策模型

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal
from datetime import date, datetime


class DataSource(BaseModel):
    """数据引用来源模型 (ISD v1.0 Section 2.5)"""

    name: str  # 数据源名称

    url: Optional[str] = None  # 原始 URL

    data_timestamp: datetime  # 数据时间戳（已通过时间隔离校验）

    market_type: Literal["US", "CN_A", "HK"]

    fetched_at: datetime  # 获取时间（UTC）


class TradeDecision(BaseModel):
    """
    标准决策模型 - ISD v1.0 Section 3

    系统最核心的输出数据结构，所有最终决策节点的输出必须严格符合此模型。
    Pydantic 校验失败时，最多重试 3 次，仍失败则输出错误记录并将 action 置为 INSUFFICIENT_DATA。
    """

    # ─── 核心决策字段 ────────────────────────────────
    action: Literal[
        "STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL", "INSUFFICIENT_DATA"
    ]

    confidence: float = Field(ge=0.0, le=1.0, description="综合置信度")

    conviction: Literal["HIGH", "MEDIUM", "LOW"]

    primary_reason: str = Field(description="主要决策理由")

    insufficient_data: bool = False  # 数据不足标志

    # ─── 价格目标 ────────────────────────────────────
    target_price_low: Optional[float] = Field(default=None, gt=0)

    target_price_high: Optional[float] = Field(default=None, gt=0)

    time_horizon: str  # 如 "2-4 weeks"

    # ─── 风险与来源 ──────────────────────────────────
    risk_factors: List[str] = Field(min_length=1)

    data_sources: List[DataSource] = Field(min_length=1)

    # ─── 元数据 ──────────────────────────────────────
    analysis_date: date  # 分析基准日期

    analysis_timestamp: datetime  # 分析完成时间（UTC）

    volatility_adjustment: float = Field(ge=0.5, le=2.0)

    debate_quality_score: float = Field(ge=0.0, le=10.0)

    symbol: str

    market_type: Literal["US", "CN_A", "HK"]

    # ─── 校验规则 ────────────────────────────────────
    @field_validator("primary_reason")
    @classmethod
    def primary_reason_length(cls, v: str) -> str:
        """primary_reason 最大长度 100 字符"""
        if len(v) > 100:
            raise ValueError("ensure this value has at most 100 characters")
        return v

    @model_validator(mode="after")
    def validate_target_prices(self) -> "TradeDecision":
        """目标价上限必须 >= 下限"""
        if self.target_price_high and self.target_price_low:
            if self.target_price_high < self.target_price_low:
                raise ValueError("目标价上限必须 >= 下限")
        return self

    @model_validator(mode="after")
    def validate_action_consistency(self) -> "TradeDecision":
        """insufficient_data=True 时 action 必须为 INSUFFICIENT_DATA"""
        if self.insufficient_data and self.action != "INSUFFICIENT_DATA":
            raise ValueError("insufficient_data=True 时 action 必须为 INSUFFICIENT_DATA")
        return self
