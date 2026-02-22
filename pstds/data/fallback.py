# pstds/data/fallback.py
# FallbackManager - 降级管理器

from typing import List, Optional, Dict, Any
from datetime import date, datetime, UTC
from pathlib import Path
import json

from pstds.temporal.context import TemporalContext


class DataQualityReport:
    """
    数据质量报告

    包含 score、missing_fields、anomaly_alerts、filtered_news_count、fallbacks_used
    """

    def __init__(
        self,
        score: float = 100.0,
        missing_fields: List[str] = None,
        anomaly_alerts: List[str] = None,
        filtered_news_count: int = 0,
        fallbacks_used: List[str] = None,
    ):
        self.score = score  # 0-100分
        self.missing_fields = missing_fields or []
        self.anomaly_alerts = anomaly_alerts or []
        self.filtered_news_count = filtered_news_count
        self.fallbacks_used = fallbacks_used or []

    def add_fallback(self, adapter_name: str) -> None:
        """记录降级使用的适配器"""
        if adapter_name not in self.fallbacks_used:
            self.fallbacks_used.append(adapter_name)
            # 降级每次扣 10 分
        self.score = max(0, self.score - 10)

    def add_missing_field(self, field: str) -> None:
        """记录缺失字段"""
        if field not in self.missing_fields:
            self.missing_fields.append(field)
            # 每个缺失字段扣 5 分
            self.score = max(0, self.score - 5)

    def add_anomaly(self, alert: str) -> None:
        """记录异常警报"""
        self.anomaly_alerts.append(alert)
        # 异常扣 15 分
        self.score = max(0, self.score - 15)

    def set_filtered_news_count(self, count: int) -> None:
        """设置被过滤的新闻数量"""
        self.filtered_news_count = count
        # 过滤超过 50% 扣分
        if count > 0:  # 简化处理
            self.score = max(0, self.score - min(count, 20))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "score": self.score,
            "missing_fields": self.missing_fields,
            "anomaly_alerts": self.anomaly_alerts,
            "filtered_news_count": self.filtered_news_count,
            "fallbacks_used": self.fallbacks_used,
            "generated_at": datetime.now(UTC).isoformat(),
        }


class FallbackManager:
    """
    降级管理器

    主源失败时按优先级尝试备用源，记录 fallback_used 到 DataQualityReport
    """

    def __init__(
        self,
        primary_adapters: List,
        fallback_adapters: List,
        report: Optional[DataQualityReport] = None,
    ):
        self.primary_adapters = primary_adapters
        self.fallback_adapters = fallback_adapters
        self.report = report or DataQualityReport()

    def get_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        interval: str,
        ctx: TemporalContext,
    ) -> Any:
        """
        获取 OHLCV 数据，支持自动降级

        按优先级尝试适配器，失败时自动切换到备用源
        """
        # 先尝试主源
        for adapter in self.primary_adapters:
            try:
                result = adapter.get_ohlcv(symbol, start_date, end_date, interval, ctx)
                if not result.empty:
                    return result
            except Exception as e:
                print(f"Primary adapter {adapter.name} failed: {e}")
                continue

        # 主源失败，尝试备用源
        for adapter in self.fallback_adapters:
            try:
                result = adapter.get_ohlcv(symbol, start_date, end_date, interval, ctx)
                if not result.empty:
                    self.report.add_fallback(adapter.name)
                    return result
            except Exception as e:
                print(f"Fallback adapter {adapter.name} failed: {e}")
                continue

        # 所有适配器都失败，返回空 DataFrame
        return None

    def get_fundamentals(
        self,
        symbol: str,
        as_of_date: date,
        ctx: TemporalContext,
    ) -> Optional[Dict]:
        """
        获取基本面数据，支持自动降级
        """
        # 先尝试主源
        for adapter in self.primary_adapters:
            try:
                result = adapter.get_fundamentals(symbol, as_of_date, ctx)
                # 检查是否有有效数据
                if any(v is not None for k, v in result.items() if k not in ["data_source", "fetched_at"]):
                    return result
            except Exception as e:
                print(f"Primary adapter {adapter.name} failed: {e}")
                continue

        # 主源失败，尝试备用源
        for adapter in self.fallback_adapters:
            try:
                result = adapter.get_fundamentals(symbol, as_of_date, ctx)
                if any(v is not None for k, v in result.items() if k not in ["data_source", "fetched_at"]):
                    self.report.add_fallback(adapter.name)
                    return result
            except Exception as e:
                print(f"Fallback adapter {adapter.name} failed: {e}")
                continue

        # 所有适配器都失败
        return None

    def get_news(
        self,
        symbol: str,
        days_back: int,
        ctx: TemporalContext,
    ) -> List:
        """
        获取新闻数据，支持自动降级
        """
        # 先尝试主源
        for adapter in self.primary_adapters:
            try:
                result = adapter.get_news(symbol, days_back, ctx)
                if result:
                    return result
            except Exception as e:
                print(f"Primary adapter {adapter.name} failed: {e}")
                continue

        # 主源失败，尝试备用源
        for adapter in self.fallback_adapters:
            try:
                result = adapter.get_news(symbol, days_back, ctx)
                if result:
                    self.report.add_fallback(adapter.name)
                    return result
            except Exception as e:
                print(f"Fallback adapter {adapter.name} failed: {e}")
                continue

        # 所有适配器都失败
        return []

    def get_report(self) -> DataQualityReport:
        """获取数据质量报告"""
        return self.report
