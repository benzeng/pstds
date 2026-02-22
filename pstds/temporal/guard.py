# pstds/temporal/guard.py
# ISD v1.0 Section 5: TemporalGuard 接口契约

from datetime import datetime, date, UTC
from typing import List

from pstds.data.models import NewsItem
from pstds.temporal.context import TemporalContext
from pstds.temporal.audit import AuditLogger, AuditRecord


class TemporalViolationError(Exception):
    """数据时间戳违反时间隔离规则时抛出"""

    def __init__(self, data_timestamp, analysis_date, caller_info: str):
        self.data_timestamp = data_timestamp
        self.analysis_date = analysis_date
        self.caller_info = caller_info
        super().__init__(
            f"时间违规: 数据时间戳 {data_timestamp} > analysis_date {analysis_date}"
            f" (调用方: {caller_info})"
        )


class RealtimeAPIBlockedError(Exception):
    """BACKTEST 模式下调用实时 API 时抛出"""
    pass


class TemporalGuard:
    """
    时间隔离守卫 - 纯静态方法类

    所有时间边界校验逻辑集中在此模块中。
    数据访问层必须在获取/过滤数据前调用此守卫。
    """

    @staticmethod
    def validate_timestamp(
        data_timestamp: datetime | date,
        ctx: TemporalContext,
        caller_info: str = "",
    ) -> None:
        """
        校验数据时间戳是否不晚于 ctx.analysis_date

        违规时：记录审计日志 + 抛出 TemporalViolationError

        Args:
            data_timestamp: 数据时间戳（datetime 或 date）
            ctx: 时间上下文
            caller_info: 调用方信息（用于审计日志）

        Raises:
            TemporalViolationError: 数据时间戳晚于分析日期时抛出
        """
        # 标准化为 date 类型再比较
        if isinstance(data_timestamp, datetime):
            data_date = data_timestamp.date()
        else:
            data_date = data_timestamp

        analysis_date = ctx.analysis_date

        if data_date > analysis_date:
            # 记录审计日志
            logger = AuditLogger()
            logger.log(
                AuditRecord(
                    timestamp=datetime.now(UTC),
                    session_id=ctx.session_id,
                    analysis_date=datetime.combine(analysis_date, datetime.min.time()),
                    data_source=caller_info,
                    data_timestamp=(
                        data_timestamp if isinstance(data_timestamp, datetime) else datetime.combine(data_date, datetime.min.time())
                    ),
                    is_compliant=False,
                    violation_detail=f"数据时间 {data_date} > 分析日期 {analysis_date}",
                    caller_module=caller_info,
                )
            )

            # 抛出异常
            raise TemporalViolationError(data_timestamp, analysis_date, caller_info)

    @staticmethod
    def filter_news(
        news_list: List[NewsItem],
        ctx: TemporalContext,
    ) -> List[NewsItem]:
        """
        过滤 published_at > ctx.analysis_date 的新闻

        记录过滤数量到审计日志

        Args:
            news_list: 新闻列表
            ctx: 时间上下文

        Returns:
            通过时间校验的 NewsItem 列表（原列表的子集）
        """
        compliant_news = []
        # 提升到循环外，避免每条新闻重复实例化
        logger = AuditLogger()

        for news in news_list:
            news_date = news.published_at.date() if isinstance(news.published_at, datetime) else news.published_at

            if news_date <= ctx.analysis_date:
                compliant_news.append(news)
            else:
                # 记录被过滤的新闻
                logger.log(
                    AuditRecord(
                        timestamp=datetime.now(UTC),
                        session_id=ctx.session_id,
                        analysis_date=datetime.combine(ctx.analysis_date, datetime.min.time()),
                        data_source=f"news:{news.source}",
                        data_timestamp=news.published_at,
                        is_compliant=False,
                        violation_detail=f"新闻时间 {news_date} > 分析日期 {ctx.analysis_date}",
                        caller_module="TemporalGuard.filter_news",
                    )
                )

        # 记录过滤总数
        filtered_count = len(news_list) - len(compliant_news)
        if filtered_count > 0:
            logger.log(
                AuditRecord(
                    timestamp=datetime.now(UTC),
                    session_id=ctx.session_id,
                    analysis_date=datetime.combine(ctx.analysis_date, datetime.min.time()),
                    data_source="news_filter",
                    data_timestamp=datetime.now(UTC),
                    is_compliant=True,
                    violation_detail=f"过滤 {filtered_count} 条未来新闻",
                    caller_module="TemporalGuard.filter_news",
                )
            )

        return compliant_news

    @staticmethod
    def assert_backtest_safe(ctx: TemporalContext, api_name: str) -> None:
        """
        BACKTEST 模式下调用实时 API 前必须调用此方法

        ctx.mode == 'BACKTEST' 时抛出 RealtimeAPIBlockedError

        Args:
            ctx: 时间上下文
            api_name: API 名称

        Raises:
            RealtimeAPIBlockedError: BACKTEST 模式下调用实时 API 时抛出
        """
        if ctx.mode == "BACKTEST":
            raise RealtimeAPIBlockedError(f"BACKTEST 模式禁止调用实时 API: {api_name}")

    @staticmethod
    def inject_temporal_prompt(base_prompt: str, ctx: TemporalContext) -> str:
        """
        在 base_prompt 前插入 ctx.get_prompt_prefix()

        返回：完整系统提示词字符串

        Args:
            base_prompt: 基础提示词
            ctx: 时间上下文

        Returns:
            完整系统提示词字符串
        """
        return ctx.get_prompt_prefix() + "\n\n" + base_prompt
