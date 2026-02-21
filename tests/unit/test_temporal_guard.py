# tests/unit/test_temporal_guard.py
# TemporalGuard 测试套件 - TG-001 至 TG-012

import pytest
from datetime import date, datetime
from pathlib import Path
import json

from pstds.temporal.context import TemporalContext
from pstds.temporal.guard import TemporalGuard, TemporalViolationError, RealtimeAPIBlockedError
from pstds.temporal.audit import AuditLogger, AuditRecord
from pstds.data.models import NewsItem


class TestTemporalGuardValidation:
    """TG-001 至 TG-004: 时间戳校验测试"""

    def test_tg001_valid_past_timestamp(self):
        """TG-001: 过去时间戳应通过校验"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))
        data_ts = date(2024, 1, 1)  # analysis_date - 1天

        # 应无异常
        TemporalGuard.validate_timestamp(data_ts, ctx, "test_module")

    def test_tg002_valid_equal_timestamp(self):
        """TG-002: 相同日期时间戳应通过校验"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))
        data_ts = datetime(2024, 1, 2, 10, 0, 0)  # 等于 analysis_date，使用 datetime 类型

        # 应无异常
        TemporalGuard.validate_timestamp(data_ts, ctx, "test_module")

    def test_tg003_future_timestamp_raises(self):
        """TG-003: 未来时间戳必须被拒绝（阻塞性测试）"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))
        data_ts = date(2024, 1, 3)  # analysis_date + 1天

        with pytest.raises(TemporalViolationError) as exc_info:
            TemporalGuard.validate_timestamp(data_ts, ctx, "test_module")

        assert "时间违规" in str(exc_info.value)
        assert "2024-01-03" in str(exc_info.value)

    def test_tg004_audit_log_on_violation(self):
        """TG-004: 违规应被记录到审计日志"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))
        data_ts = date(2024, 1, 3)

        # 确保审计日志文件存在
        audit_log_path = Path("./data/logs/temporal_audit.jsonl")
        if audit_log_path.exists():
            audit_log_path.unlink()

        # 触发违规
        try:
            TemporalGuard.validate_timestamp(data_ts, ctx, "test_tg004")
        except TemporalViolationError:
            pass

        # 检查审计日志
        logger = AuditLogger()
        violation_count = logger.get_violation_count(ctx.session_id)
        assert violation_count >= 1, "审计日志应记录至少一次违规"


class TestTemporalGuardNewsFilter:
    """TG-005 至 TG-007: 新闻过滤测试"""

    def test_tg005_news_filter_removes_future(self):
        """TG-005: 新闻过滤应移除未来日期的条目"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))

        # 创建测试新闻列表：5条合规 + 3条未来
        news_list = []
        # 前5条在 analysis_date (2024-01-02) 之前或当天
        valid_dates = [1, 1, 2, 2, 2]  # 1月1日和1月2日
        for i, day in enumerate(valid_dates):
            news_list.append(NewsItem(
                title=f"Valid News {i}",
                content=f"Content {i}",
                published_at=datetime(2024, 1, day, 10 + i, 0, 0),
                source="Test",
                relevance_score=0.8,
                market_type="US",
                symbol="AAPL"
            ))

        for i in range(3):
            news_list.append(NewsItem(
                title=f"Future News {i}",
                content=f"Content {i}",
                published_at=datetime(2024, 1, 3 + i, 10, 0, 0),  # 未来日期
                source="Test",
                relevance_score=0.8,
                market_type="US",
                symbol="AAPL"
            ))

        filtered = TemporalGuard.filter_news(news_list, ctx)

        assert len(filtered) == 5, f"应返回5条合规新闻，实际返回{len(filtered)}条"

        # 检查审计日志
        logger = AuditLogger()
        records = logger.get_session_records(ctx.session_id)
        violation_records = [r for r in records if not r.get("is_compliant", True)]
        assert len(violation_records) >= 3, f"应记录至少3条过滤记录"

    def test_tg006_news_filter_all_compliant(self):
        """TG-006: 全部新闻合规时应返回原列表"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))

        news_list = []
        # 所有新闻都在 analysis_date (2024-01-02) 之前或当天
        for i in range(5):
            news_list.append(NewsItem(
                title=f"News {i}",
                content=f"Content {i}",
                published_at=datetime(2024, 1, 1, 10 + i, 0, 0),  # 1月1日
                source="Test",
                relevance_score=0.8,
                market_type="US",
                symbol="AAPL"
            ))

        filtered = TemporalGuard.filter_news(news_list, ctx)

        assert len(filtered) == 5
        # 所有新闻应与原列表相同
        assert all(n in news_list for n in filtered)

    def test_tg007_news_filter_all_future(self):
        """TG-007: 全部新闻为未来时应返回空列表"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))

        news_list = []
        for i in range(3):
            news_list.append(NewsItem(
                title=f"Future News {i}",
                content=f"Content {i}",
                published_at=datetime(2024, 1, 3 + i, 10, 0, 0),  # 全部未来
                source="Test",
                relevance_score=0.8,
                market_type="US",
                symbol="AAPL"
            ))

        filtered = TemporalGuard.filter_news(news_list, ctx)

        assert len(filtered) == 0, "应返回空列表"


class TestTemporalGuardBacktestSafety:
    """TG-008 至 TG-009: BACKTEST 安全测试"""

    def test_tg008_backtest_blocks_realtime(self):
        """TG-008: BACKTEST 模式禁止调用实时 API（阻塞性测试）"""
        ctx = TemporalContext.for_backtest(date(2024, 1, 2))

        with pytest.raises(RealtimeAPIBlockedError) as exc_info:
            TemporalGuard.assert_backtest_safe(ctx, "test_api")

        assert "BACKTEST 模式禁止调用实时 API" in str(exc_info.value)
        assert "test_api" in str(exc_info.value)

    def test_tg009_live_allows_realtime(self):
        """TG-009: LIVE 模式应允许实时 API"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))

        # 应无异常
        TemporalGuard.assert_backtest_safe(ctx, "test_api")


class TestTemporalGuardPromptInjection:
    """TG-010: 提示词注入测试"""

    def test_tg010_prompt_injection_contains_date(self):
        """TG-010: 提示词注入应包含分析日期"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))
        base_prompt = "请分析这只股票。"

        result = TemporalGuard.inject_temporal_prompt(base_prompt, ctx)

        assert "2024-01-02" in result, "返回字符串应包含分析日期"
        assert result.startswith("【时间隔离声明】"), "时间声明必须在最前面"
        assert "请分析这只股票。" in result, "应包含原始提示词"
        assert base_prompt in result, "原始提示词应被保留"


class TestTemporalContextImmutability:
    """TG-011: 不可变性测试"""

    def test_tg011_context_immutable(self):
        """TG-011: TemporalContext 必须是不可变的"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))

        with pytest.raises(Exception):  # FrozenInstanceError
            ctx.analysis_date = date(2024, 1, 3)


class TestTemporalGuardAaplLookahead:
    """TG-012: AAPL 前视偏差回归测试"""

    def test_tg012_aapl_lookahead_regression(self):
        """TG-012: AAPL 前视偏差消除验证"""
        ctx = TemporalContext.for_live(date(2024, 1, 2))

        # 创建包含未来新闻的测试数据
        fixture_path = Path(__file__).parent.parent / "fixtures" / "news" / "mixed_dates.json"
        if fixture_path.exists():
            news_data = json.loads(fixture_path.read_text(encoding="utf-8"))
            news_list = [NewsItem(**n) for n in news_data]

            filtered = TemporalGuard.filter_news(news_list, ctx)

            # 不应返回 2024-01-02 之后的任何新闻
            for news in filtered:
                assert news.published_at.date() <= date(2024, 1, 2), \
                    f"发现未来新闻: {news.title} (published_at: {news.published_at})"
        else:
            # 如果 fixture 不存在，创建简单测试
            news_list = [
                NewsItem(
                    title="Past news",
                    content="Content",
                    published_at=datetime(2024, 1, 1, 10, 0, 0),
                    source="Test",
                    relevance_score=0.8,
                    market_type="US",
                    symbol="AAPL"
                ),
                NewsItem(
                    title="Future news",
                    content="Content",
                    published_at=datetime(2024, 1, 3, 10, 0, 0),
                    source="Test",
                    relevance_score=0.8,
                    market_type="US",
                    symbol="AAPL"
                ),
            ]

            filtered = TemporalGuard.filter_news(news_list, ctx)

            assert len(filtered) == 1
            assert filtered[0].title == "Past news"


class TestAuditLogger:
    """AuditLogger 测试 - 提高覆盖率"""

    def test_get_session_records_from_existing_log(self):
        """测试从现有日志获取记录"""
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test_audit.jsonl"
            logger = AuditLogger(str(log_path))

            # 写入一些测试记录
            ctx = TemporalContext.for_live(date(2024, 1, 2))
            logger.log(AuditRecord(
                timestamp=datetime(2024, 1, 2, 10, 0, 0),
                session_id=ctx.session_id,
                analysis_date=datetime(2024, 1, 2, 0, 0, 0),
                data_source="test",
                data_timestamp=datetime(2024, 1, 1, 0, 0, 0),
                is_compliant=True,
                violation_detail="test",
                caller_module="test"
            ))

            logger.log(AuditRecord(
                timestamp=datetime(2024, 1, 2, 11, 0, 0),
                session_id=ctx.session_id,
                analysis_date=datetime(2024, 1, 2, 0, 0, 0),
                data_source="test",
                data_timestamp=datetime(2024, 1, 1, 0, 0, 0),
                is_compliant=False,
                violation_detail="test violation",
                caller_module="test"
            ))

            # 获取记录
            records = logger.get_session_records(ctx.session_id)
            assert len(records) == 2

    def test_get_session_records_from_nonexistent_log(self):
        """测试从不存在的日志获取记录"""
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "nonexistent.jsonl"
            logger = AuditLogger(str(log_path))

            ctx = TemporalContext.for_live(date(2024, 1, 2))

            # 不应抛出异常，返回空列表
            records = logger.get_session_records(ctx.session_id)
            assert records == []

    def test_get_violation_count_zero(self):
        """测试无违规时的计数"""
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test_audit.jsonl"
            logger = AuditLogger(str(log_path))

            ctx = TemporalContext.for_live(date(2024, 1, 2))

            # 只写入合规记录
            logger.log(AuditRecord(
                timestamp=datetime(2024, 1, 2, 10, 0, 0),
                session_id=ctx.session_id,
                analysis_date=datetime(2024, 1, 2, 0, 0, 0),
                data_source="test",
                data_timestamp=datetime(2024, 1, 1, 0, 0, 0),
                is_compliant=True,
                violation_detail="test",
                caller_module="test"
            ))

            # 违规计数应为 0
            count = logger.get_violation_count(ctx.session_id)
            assert count == 0

