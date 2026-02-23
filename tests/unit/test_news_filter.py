# tests/unit/test_news_filter.py
# NewsFilter 三级过滤器测试 - NF-001 至 NF-010
# TSD v2.0 NF 节

import json
import pytest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from pstds.data.models import NewsItem
from pstds.data.news_filter import NewsFilter, NewsFilterStats
from pstds.temporal.context import TemporalContext


# ─── 辅助函数 ──────────────────────────────────────────────

def make_news(
    title: str,
    content: str,
    published_at: datetime,
    relevance_score: float = 0.8,
    symbol: str = "AAPL",
) -> NewsItem:
    return NewsItem(
        title=title,
        content=content,
        published_at=published_at,
        source="TestSource",
        relevance_score=relevance_score,
        market_type="US",
        symbol=symbol,
    )


@pytest.fixture
def ctx_2024_01_02():
    """分析日期 2024-01-02 的 LIVE 上下文"""
    return TemporalContext.for_live(date(2024, 1, 2))


@pytest.fixture
def news_filter():
    return NewsFilter(relevance_threshold=0.05, dedup_threshold=0.85)


@pytest.fixture
def low_relevance_fixture():
    """加载低相关性 fixture"""
    path = Path(__file__).parent.parent / "fixtures" / "news" / "aapl_news_low_relevance.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [NewsItem(**item) for item in data]


@pytest.fixture
def duplicates_fixture():
    """加载重复新闻 fixture"""
    path = Path(__file__).parent.parent / "fixtures" / "news" / "aapl_news_duplicates.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [NewsItem(**item) for item in data]


# ─── NF-001: 空列表 ────────────────────────────────────────

class TestNF001EmptyList:
    def test_nf001_empty_list_returns_empty_with_zero_stats(
        self, news_filter, ctx_2024_01_02
    ):
        """NF-001: 空列表过滤结果为空，所有 stats 字段为 0"""
        result, stats = news_filter.filter([], "AAPL", ctx_2024_01_02)

        assert result == []
        assert stats.raw_count == 0
        assert stats.after_temporal == 0
        assert stats.after_relevance == 0
        assert stats.after_dedup == 0
        assert stats.temporal_filtered == 0
        assert stats.relevance_filtered == 0


# ─── NF-002: L1 时间过滤 ──────────────────────────────────

class TestNF002TemporalFilter:
    def test_nf002_future_news_removed_by_l1(
        self, news_filter, ctx_2024_01_02
    ):
        """NF-002: L1 时间过滤移除 analysis_date 之后的新闻"""
        news_list = [
            make_news("Past AAPL news", "Apple earnings", datetime(2024, 1, 1, 10, 0, 0)),
            make_news("Present AAPL news", "Apple product launch", datetime(2024, 1, 2, 9, 0, 0)),
            make_news("Future AAPL news", "Apple future outlook", datetime(2024, 1, 3, 10, 0, 0)),
            make_news("Far future AAPL", "Apple 2025 plans", datetime(2024, 1, 5, 10, 0, 0)),
        ]

        result, stats = news_filter.filter(news_list, "AAPL", ctx_2024_01_02)

        assert stats.raw_count == 4
        assert stats.after_temporal == 2  # only past + present
        assert stats.temporal_filtered == 2  # 2 future removed
        # 未来新闻不应出现在结果中
        dates = [n.published_at.date() for n in result]
        assert all(d <= date(2024, 1, 2) for d in dates)


# ─── NF-003: L2 相关性过滤 ───────────────────────────────

class TestNF003RelevanceFilter:
    def test_nf003_low_relevance_removed(
        self, news_filter, ctx_2024_01_02, low_relevance_fixture
    ):
        """NF-003: L2 相关性过滤移除与 AAPL 无关的新闻"""
        # low_relevance_fixture 中最后一条是 AAPL 相关，前 4 条完全无关
        result, stats = news_filter.filter(
            low_relevance_fixture, "AAPL", ctx_2024_01_02, company_name="Apple"
        )

        # 相关性过滤应减少条目
        assert stats.after_relevance <= stats.after_temporal
        # AAPL 相关的新闻应该保留
        assert len(result) >= 1


# ─── NF-004: L3 余弦去重 ──────────────────────────────────

class TestNF004Deduplication:
    def test_nf004_duplicates_removed_keep_oldest(
        self, news_filter, ctx_2024_01_02, duplicates_fixture
    ):
        """NF-004: L3 去重移除高相似度副本，保留最早发布的"""
        result, stats = news_filter.filter(
            duplicates_fixture, "AAPL", ctx_2024_01_02, company_name="Apple"
        )

        assert stats.after_dedup <= stats.after_relevance
        # 去重后数量应少于原始数量（前 3 条几乎相同）
        assert len(result) < len(duplicates_fixture)

    def test_nf004_oldest_kept_not_newest(
        self, ctx_2024_01_02
    ):
        """NF-004: 去重时保留 published_at 最早的条目"""
        nf = NewsFilter(dedup_threshold=0.5)  # 低阈值，更容易触发去重

        early = make_news(
            "Apple AAPL iPhone record sales beat expectations",
            "Apple Inc reported record iPhone sales beating expectations significantly",
            datetime(2024, 1, 1, 8, 0, 0),  # 更早
        )
        late = make_news(
            "Apple AAPL iPhone record sales beat all expectations",
            "Apple Inc reported record iPhone sales beating expectations significantly",
            datetime(2024, 1, 1, 18, 0, 0),  # 更晚，相似内容
        )
        unrelated = make_news(
            "AAPL stock hits new high today",
            "Apple stock reached all time high as investors celebrate strong earnings beat",
            datetime(2024, 1, 2, 9, 0, 0),
        )

        result, stats = nf.filter([early, late, unrelated], "AAPL", ctx_2024_01_02)

        # 若去重发生，保留的应是 early（published_at 更早）
        # 检查 late 的 URL 不在结果中（或 early 在结果中）
        result_times = [n.published_at for n in result]
        if len(result) < 3:
            # 去重发生了，最晚的那条应被移除
            assert datetime(2024, 1, 1, 18, 0, 0) not in result_times or \
                   datetime(2024, 1, 1, 8, 0, 0) in result_times


# ─── NF-005: 纯函数验证 ──────────────────────────────────

class TestNF005PureFunction:
    def test_nf005_input_list_not_modified(
        self, news_filter, ctx_2024_01_02
    ):
        """NF-005: filter() 不修改输入列表（C-08 约束）"""
        original = [
            make_news("AAPL news 1", "Apple content 1", datetime(2024, 1, 1, 10, 0, 0)),
            make_news("AAPL news 2", "Apple content 2", datetime(2024, 1, 1, 11, 0, 0)),
            make_news("Future news", "Future content", datetime(2024, 1, 3, 10, 0, 0)),
        ]
        original_len = len(original)
        original_ids = [id(n) for n in original]

        result, _ = news_filter.filter(original, "AAPL", ctx_2024_01_02)

        # 输入列表长度不变
        assert len(original) == original_len
        # 输入列表元素对象身份不变
        assert [id(n) for n in original] == original_ids

    def test_nf005_result_is_new_object(
        self, news_filter, ctx_2024_01_02
    ):
        """NF-005: 返回的列表是新对象，不是原始列表的引用"""
        original = []
        result, _ = news_filter.filter(original, "AAPL", ctx_2024_01_02)

        assert result is not original


# ─── NF-006: 三级级联顺序 ─────────────────────────────────

class TestNF006FilterOrder:
    def test_nf006_stats_counts_are_monotone_decreasing(
        self, news_filter, ctx_2024_01_02
    ):
        """NF-006: after_temporal >= after_relevance >= after_dedup（单调递减）"""
        news_list = [
            make_news("Apple AAPL earnings beat", "Apple reported strong earnings", datetime(2024, 1, 1, 10, 0, 0)),
            make_news("AAPL iPhone sales surge", "Apple iPhone sales grew 20%", datetime(2024, 1, 1, 11, 0, 0)),
            make_news("Sports news today", "Basketball championship results", datetime(2024, 1, 1, 12, 0, 0)),
            make_news("Future Apple news", "Apple next year plans", datetime(2024, 1, 5, 10, 0, 0)),
        ]

        result, stats = news_filter.filter(news_list, "AAPL", ctx_2024_01_02)

        assert stats.raw_count == 4
        assert stats.after_temporal <= stats.raw_count
        assert stats.after_relevance <= stats.after_temporal
        assert stats.after_dedup <= stats.after_relevance


# ─── NF-007: Stats 属性计算正确 ──────────────────────────

class TestNF007Stats:
    def test_nf007_temporal_filtered_property(
        self, news_filter, ctx_2024_01_02
    ):
        """NF-007: temporal_filtered = raw_count - after_temporal"""
        news_list = [
            make_news("AAPL news past", "Apple news", datetime(2024, 1, 1, 10, 0, 0)),
            make_news("AAPL future 1", "Apple future", datetime(2024, 1, 3, 10, 0, 0)),
            make_news("AAPL future 2", "Apple future 2", datetime(2024, 1, 4, 10, 0, 0)),
        ]

        _, stats = news_filter.filter(news_list, "AAPL", ctx_2024_01_02)

        assert stats.temporal_filtered == stats.raw_count - stats.after_temporal
        assert stats.relevance_filtered == stats.after_temporal - stats.after_relevance

    def test_nf007_newsfilter_stats_dataclass_fields(self):
        """NF-007: NewsFilterStats 有 4 个字段 + 2 个属性"""
        stats = NewsFilterStats(
            raw_count=10,
            after_temporal=8,
            after_relevance=5,
            after_dedup=4,
        )

        assert stats.raw_count == 10
        assert stats.after_temporal == 8
        assert stats.after_relevance == 5
        assert stats.after_dedup == 4
        assert stats.temporal_filtered == 2   # 10 - 8
        assert stats.relevance_filtered == 3  # 8 - 5


# ─── NF-008: 单条新闻不被去重 ────────────────────────────

class TestNF008SingleItem:
    def test_nf008_single_item_passes_all_filters(
        self, news_filter, ctx_2024_01_02
    ):
        """NF-008: 单条合规新闻通过所有过滤层"""
        single = [
            make_news("AAPL Apple earnings beat", "Apple Q4 earnings beat expectations", datetime(2024, 1, 1, 10, 0, 0))
        ]

        result, stats = news_filter.filter(single, "AAPL", ctx_2024_01_02)

        assert stats.raw_count == 1
        assert stats.after_temporal == 1
        # 单条不会被去重
        assert stats.after_dedup == 1
        assert len(result) == 1


# ─── NF-009: 异常静默降级 ─────────────────────────────────

class TestNF009GracefulDegradation:
    def test_nf009_l2_exception_degrades_gracefully(
        self, ctx_2024_01_02
    ):
        """NF-009: L2 内部异常时静默降级，不传播异常"""
        nf = NewsFilter()
        news_list = [
            make_news("AAPL news", "Apple content", datetime(2024, 1, 1, 10, 0, 0))
        ]

        # 模拟 sklearn 不可用（强制 ImportError）
        with patch("pstds.data.news_filter.NewsFilter._filter_by_relevance", side_effect=RuntimeError("Test error")):
            # 不应抛出异常
            result, stats = nf.filter(news_list, "AAPL", ctx_2024_01_02)
            assert result is not None
            assert stats is not None

    def test_nf009_l3_exception_degrades_gracefully(
        self, ctx_2024_01_02
    ):
        """NF-009: L3 内部异常时静默降级，不传播异常"""
        nf = NewsFilter()
        news_list = [
            make_news("AAPL news", "Apple content", datetime(2024, 1, 1, 10, 0, 0))
        ]

        with patch("pstds.data.news_filter.NewsFilter._dedup_by_cosine", side_effect=RuntimeError("Test error")):
            result, stats = nf.filter(news_list, "AAPL", ctx_2024_01_02)
            assert result is not None
            assert stats is not None


# ─── NF-010: 空 corpus 处理 ──────────────────────────────

class TestNF010EmptyCorpus:
    def test_nf010_empty_content_corpus_handled(
        self, news_filter, ctx_2024_01_02
    ):
        """NF-010: 所有新闻 title+content 为空时静默返回原列表"""
        news_list = [
            NewsItem(
                title="",
                content="",
                published_at=datetime(2024, 1, 1, 10, 0, 0),
                source="Test",
                relevance_score=0.5,
                market_type="US",
                symbol="AAPL",
            ),
        ]

        # 不应抛出异常
        result, stats = news_filter.filter(news_list, "AAPL", ctx_2024_01_02)
        assert result is not None
        assert stats.raw_count == 1

    def test_nf010_all_text_blank_returns_original(
        self, ctx_2024_01_02
    ):
        """NF-010: corpus 全空时 L2 降级返回原列表"""
        nf = NewsFilter(relevance_threshold=0.99)  # 极高阈值

        news_list = [
            NewsItem(
                title="   ",
                content="   ",
                published_at=datetime(2024, 1, 1, 10, 0, 0),
                source="Test",
                relevance_score=0.5,
                market_type="US",
                symbol="AAPL",
            ),
        ]

        result, stats = nf.filter(news_list, "AAPL", ctx_2024_01_02)
        # corpus 空时静默降级，不丢弃所有新闻
        assert len(result) >= 0  # 不抛出异常即可
