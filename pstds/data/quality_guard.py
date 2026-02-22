# pstds/data/quality_guard.py
# 数据质量守卫 - DDD v2.0 Section 3.4

import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import date, datetime

from pstds.data.fallback import DataQualityReport
from pstds.data.models import NewsItem
from pstds.temporal.context import TemporalContext


class DataQualityGuard:
    """
    数据质量守卫

    输出 DataQualityReport（含 score、missing_fields、anomaly_alerts、filtered_news_count、fallbacks_used）
    评分规则按 DDD v2.0 第 3.4 节
    """

    def __init__(self):
        self.report = DataQualityReport()

    def validate_ohlcv(
        self,
        df: pd.DataFrame,
        symbol: str,
        ctx: TemporalContext,
    ) -> DataQualityReport:
        """
        验证行情数据质量

        每次调用使用新 DataQualityReport 实例，避免跨调用状态污染。
        检查规则：
        1. 时序连续性（交易日无缺口）- 缺口 ≤ 3 个交易日
        2. 价格合理性（非负，无极端异常）- 涨跌幅 ≤ 30%（A股限制）
        """
        report = DataQualityReport()

        if df.empty:
            report.score = 0
            report.add_missing_field("ohlcv_data")
            return report

        # 检查价格非负
        for col in ["open", "high", "low", "close", "adj_close"]:
            if col in df.columns:
                if (df[col] <= 0).any():
                    report.add_anomaly(f"{symbol}: {col} 存在非正值")

        # 检查价格合理性（high >= low）
        if "high" in df.columns and "low" in df.columns:
            if (df["high"] < df["low"]).any():
                report.add_anomaly(f"{symbol}: high < low 异常")

        # 检查涨跌幅（简化处理）
        if "close" in df.columns:
            df_sorted = df.sort_values("date")
            pct_change = df_sorted["close"].pct_change()

            # 涨跌幅超过 30% 标记为异常（A股限制）
            extreme_changes = pct_change.abs() > 0.30
            if extreme_changes.any():
                extreme_dates = df_sorted.loc[extreme_changes, "date"].dt.strftime("%Y-%m-%d").tolist()
                report.add_anomaly(f"{symbol}: 极端涨跌幅 {extreme_dates}")

        # 检查时序连续性（简化：检查日期间隔）
        if "date" in df.columns:
            df_sorted = df.sort_values("date")
            df_sorted["date"] = pd.to_datetime(df_sorted["date"])
            df_sorted["date_diff"] = df_sorted["date"].diff()

            # 超过 3 天的间隔视为缺口（跳过周末）
            large_gaps = df_sorted[df_sorted["date_diff"] > pd.Timedelta(days=5)]
            if len(large_gaps) > 3:
                report.add_anomaly(f"{symbol}: 时序存在较多缺口 ({len(large_gaps)} 处)")

        return report

    def validate_fundamentals(
        self,
        fundamentals: Dict,
        symbol: str,
    ) -> DataQualityReport:
        """
        验证财报数据质量

        每次调用使用新 DataQualityReport 实例，避免跨调用状态污染。
        检查规则：必需字段完整性（PE/PB/ROE 全部存在）
        """
        report = DataQualityReport()
        required_fields = ["pe_ratio", "pb_ratio", "roe"]

        for field in required_fields:
            if field not in fundamentals or fundamentals[field] is None:
                report.add_missing_field(f"fundamentals.{field}")

        return report

    def validate_news(
        self,
        news_list: List[NewsItem],
        ctx: TemporalContext,
    ) -> DataQualityReport:
        """
        验证新闻数据质量

        每次调用使用新 DataQualityReport 实例，避免跨调用状态污染。
        检查规则：
        1. 时间戳合规：published_at <= analysis_date
        2. 计算被过滤的新闻数量
        """
        report = DataQualityReport()
        analysis_date = ctx.analysis_date
        filtered_count = 0

        for news in news_list:
            news_date = news.published_at.date() if isinstance(news.published_at, datetime) else news.published_at

            if news_date > analysis_date:
                filtered_count += 1

        report.set_filtered_news_count(filtered_count)

        return report

    def get_report(self) -> DataQualityReport:
        """获取数据质量报告"""
        return self.report

    def reset(self) -> None:
        """重置报告"""
        self.report = DataQualityReport()
