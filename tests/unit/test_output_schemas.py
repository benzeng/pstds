# tests/unit/test_output_schemas.py
# 数据模型（Pydantic）测试套件 - PM-001 至 PM-008

import pytest
from datetime import date, datetime
from pydantic import ValidationError

from pstds.agents.output_schemas import TradeDecision, DataSource
from pstds.data.models import NewsItem, OHLCVRecord


class TestTradeDecisionModel:
    """PM-001 至 PM-006: TradeDecision 模型测试"""

    def test_pm001_valid_trade_decision(self):
        """PM-001: 有效的 TradeDecision 应创建成功"""
        decision = TradeDecision(
            action="BUY",
            confidence=0.72,
            conviction="MEDIUM",
            primary_reason="技术面突破",
            insufficient_data=False,
            target_price_low=180.0,
            target_price_high=195.0,
            time_horizon="2-4 weeks",
            risk_factors=["市场波动", "估值风险"],
            data_sources=[
                DataSource(
                    name="yfinance",
                    data_timestamp=datetime(2024, 1, 2, 0, 0, 0),
                    market_type="US",
                    fetched_at=datetime(2024, 1, 2, 9, 0, 0),
                )
            ],
            analysis_date=date(2024, 1, 2),
            analysis_timestamp=datetime(2024, 1, 2, 10, 0, 0),
            volatility_adjustment=1.0,
            debate_quality_score=7.5,
            symbol="AAPL",
            market_type="US",
        )

        assert decision.action == "BUY"
        assert decision.confidence == 0.72
        assert decision.conviction == "MEDIUM"

    def test_pm002_confidence_out_of_range(self):
        """PM-002: confidence 超出范围应抛出 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            TradeDecision(
                action="BUY",
                confidence=1.5,  # 超出范围
                conviction="MEDIUM",
                primary_reason="测试",
                risk_factors=["风险"],
                data_sources=[
                    DataSource(
                        name="yfinance",
                        data_timestamp=datetime(2024, 1, 2, 0, 0, 0),
                        market_type="US",
                        fetched_at=datetime(2024, 1, 2, 9, 0, 0),
                    )
                ],
                time_horizon="1 week",
                analysis_date=date(2024, 1, 2),
                analysis_timestamp=datetime(2024, 1, 2, 10, 0, 0),
                volatility_adjustment=1.0,
                debate_quality_score=5.0,
                symbol="AAPL",
                market_type="US",
            )

        assert "input should be less than or equal to 1" in str(exc_info.value).lower()

    def test_pm003_insufficient_data_inconsistent_action(self):
        """PM-003: insufficient_data=True 时 action 必须为 INSUFFICIENT_DATA"""
        with pytest.raises(ValidationError) as exc_info:
            TradeDecision(
                action="BUY",  # 与 insufficient_data=True 矛盾
                insufficient_data=True,
                confidence=0.5,
                conviction="LOW",
                primary_reason="测试",
                risk_factors=["风险"],
                data_sources=[
                    DataSource(
                        name="yfinance",
                        data_timestamp=datetime(2024, 1, 2, 0, 0, 0),
                        market_type="US",
                        fetched_at=datetime(2024, 1, 2, 9, 0, 0),
                    )
                ],
                time_horizon="1 week",
                analysis_date=date(2024, 1, 2),
                analysis_timestamp=datetime(2024, 1, 2, 10, 0, 0),
                volatility_adjustment=1.0,
                debate_quality_score=5.0,
                symbol="AAPL",
                market_type="US",
            )

        assert "insufficient_data=True 时 action 必须为 INSUFFICIENT_DATA" in str(exc_info.value)

    def test_pm004_target_price_high_less_than_low(self):
        """PM-004: target_price_high 必须 >= target_price_low"""
        with pytest.raises(ValidationError) as exc_info:
            TradeDecision(
                action="HOLD",
                confidence=0.5,
                conviction="LOW",
                primary_reason="测试",
                target_price_low=195.0,
                target_price_high=180.0,  # 小于 low
                risk_factors=["风险"],
                data_sources=[
                    DataSource(
                        name="yfinance",
                        data_timestamp=datetime(2024, 1, 2, 0, 0, 0),
                        market_type="US",
                        fetched_at=datetime(2024, 1, 2, 9, 0, 0),
                    )
                ],
                time_horizon="1 week",
                analysis_date=date(2024, 1, 2),
                analysis_timestamp=datetime(2024, 1, 2, 10, 0, 0),
                volatility_adjustment=1.0,
                debate_quality_score=5.0,
                symbol="AAPL",
                market_type="US",
            )

        assert "目标价上限必须 >= 下限" in str(exc_info.value)

    def test_pm005_empty_risk_factors(self):
        """PM-005: risk_factors 空列表应抛出 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            TradeDecision(
                action="HOLD",
                confidence=0.5,
                conviction="LOW",
                primary_reason="测试",
                risk_factors=[],  # 空列表
                data_sources=[
                    DataSource(
                        name="yfinance",
                        data_timestamp=datetime(2024, 1, 2, 0, 0, 0),
                        market_type="US",
                        fetched_at=datetime(2024, 1, 2, 9, 0, 0),
                    )
                ],
                time_horizon="1 week",
                analysis_date=date(2024, 1, 2),
                analysis_timestamp=datetime(2024, 1, 2, 10, 0, 0),
                volatility_adjustment=1.0,
                debate_quality_score=5.0,
                symbol="AAPL",
                market_type="US",
            )

        assert "at least 1 item" in str(exc_info.value).lower() or "ensure this value has at least 1 items" in str(exc_info.value).lower()

    def test_pm006_primary_reason_too_long(self):
        """PM-006: primary_reason 超过 100 字应抛出 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            TradeDecision(
                action="HOLD",
                confidence=0.5,
                conviction="LOW",
                primary_reason="这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的理由非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长",  # >100字
                risk_factors=["风险"],
                data_sources=[
                    DataSource(
                        name="yfinance",
                        data_timestamp=datetime(2024, 1, 2, 0, 0, 0),
                        market_type="US",
                        fetched_at=datetime(2024, 1, 2, 9, 0, 0),
                    )
                ],
                time_horizon="1 week",
                analysis_date=date(2024, 1, 2),
                analysis_timestamp=datetime(2024, 1, 2, 10, 0, 0),
                volatility_adjustment=1.0,
                debate_quality_score=5.0,
                symbol="AAPL",
                market_type="US",
            )

        assert "ensure this value has at most 100 characters" in str(exc_info.value).lower()


class TestOHLCVRecordModel:
    """PM-007: OHLCVRecord 模型测试"""

    def test_pm007_high_less_than_low(self):
        """PM-007: OHLCVRecord: high < low 应抛出 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            OHLCVRecord(
                symbol="AAPL",
                date=datetime(2024, 1, 2, 0, 0, 0),
                open=180.0,
                high=185.0,
                low=190.0,  # 高价低于低价
                close=187.0,
                volume=1000000,
                data_source="yfinance",
                fetched_at=datetime(2024, 1, 2, 9, 0, 0),
            )

        assert "high 必须 >= low" in str(exc_info.value)


class TestNewsItemModel:
    """PM-008: NewsItem 模型测试"""

    def test_pm008_relevance_score_invalid(self):
        """PM-008: NewsItem: relevance_score 超出范围应抛出 ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            NewsItem(
                title="测试新闻",
                content="测试内容",
                published_at=datetime(2024, 1, 2, 10, 0, 0),
                source="Test",
                relevance_score=-0.1,  # 超出范围
                market_type="US",
                symbol="AAPL",
            )

        assert "relevance_score 必须在 0-1 之间" in str(exc_info.value)
