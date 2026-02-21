# tests/integration/test_full_analysis_flow.py
import json
import pytest
from datetime import date, datetime, UTC
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock

from pstds.temporal.context import TemporalContext
from pstds.agents.output_schemas import TradeDecision, DataSource


@pytest.fixture
def valid_decision_json():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "llm_responses" / "valid_trade_decision.json"
    # 如果 fixture 文件不存在，返回默认的测试数据
    if not fixture_path.exists():
        return {
            "action": "BUY",
            "confidence": 0.75,
            "conviction": "MEDIUM",
            "primary_reason": "Technical breakthrough",
            "symbol": "AAPL",
            "data_sources": [{"name": "test", "url": None, "data_timestamp": datetime.now(UTC).isoformat(), "market_type": "US", "fetched_at": datetime.now(UTC).isoformat()}],
            "time_horizon": "2-4 weeks"
        }
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@pytest.fixture
def live_ctx_2024_01_02():
    return TemporalContext.for_live(date(2024, 1, 2))


class TestFullAnalysisFlow:
    def test_int001_trade_decision_structure_complete(self, valid_decision_json):
        assert "action" in valid_decision_json
        assert "confidence" in valid_decision_json
        assert 0.0 <= valid_decision_json["confidence"] <= 1.0
        assert "symbol" in valid_decision_json
        assert "data_sources" in valid_decision_json
        assert len(valid_decision_json["data_sources"]) >= 1

    def test_int002_temporal_context_in_propagation(self, live_ctx_2024_01_02, valid_decision_json):
        assert live_ctx_2024_01_02.analysis_date == date(2024, 1, 2)

    def test_int003_pydantic_validation_success(self, live_ctx_2024_01_02, valid_decision_json):
        decision = TradeDecision(
            action=valid_decision_json["action"], confidence=valid_decision_json["confidence"],
            conviction=valid_decision_json.get("conviction", "MEDIUM"),
            primary_reason=valid_decision_json.get("primary_reason", "Test"),
            insufficient_data=False, target_price_low=valid_decision_json.get("target_price_low"),
            target_price_high=valid_decision_json.get("target_price_high"),
            time_horizon=valid_decision_json.get("time_horizon", "2-4 weeks") or "1 month",
            risk_factors=valid_decision_json.get("risk_factors", ["market"]),
            data_sources=[DataSource(name="test", url=None, data_timestamp=datetime.now(UTC), market_type="US", fetched_at=datetime.now(UTC))],
            analysis_date=date(2024, 1, 2), analysis_timestamp=datetime.now(UTC), volatility_adjustment=1.0,
            debate_quality_score=7.5, symbol=valid_decision_json.get("symbol", "AAPL"), market_type="US",
        )
        assert decision.action == valid_decision_json["action"]

    def test_int004_pydantic_validation_insufficient_data(self, live_ctx_2024_01_02, valid_decision_json):
        decision = TradeDecision(
            action="INSUFFICIENT_DATA", confidence=0.0, conviction="LOW", primary_reason="Insufficient data",
            insufficient_data=True, target_price_low=None, target_price_high=None, time_horizon="",
            risk_factors=["Data unavailable"], data_sources=[DataSource(name="error", url=None, data_timestamp=datetime.now(UTC), market_type="US", fetched_at=datetime.now(UTC))], analysis_date=date(2024, 1, 2),
            analysis_timestamp=datetime.now(UTC), volatility_adjustment=1.0,
            debate_quality_score=0.0, symbol="AAPL", market_type="US",
        )
        assert decision.action == "INSUFFICIENT_DATA"

    def test_int005_pydantic_validation_invalid_action(self, live_ctx_2024_01_02, valid_decision_json):
        with pytest.raises(Exception):
            TradeDecision(
                action="INVALID_ACTION", confidence=0.5, conviction="MEDIUM", primary_reason="Test",
                insufficient_data=False, target_price_low=180.0, target_price_high=195.0, time_horizon="2-4 weeks",
                risk_factors=["market"], data_sources=[DataSource(name="test", url=None, data_timestamp=datetime.now(UTC), market_type="US", fetched_at=datetime.now(UTC))],
                analysis_date=date(2024, 1, 2), analysis_timestamp=datetime.now(UTC), volatility_adjustment=1.0,
                debate_quality_score=7.5, symbol="AAPL", market_type="US",
            )

    def test_int006_cost_estimator_price_table(self):
        from pstds.llm.cost_estimator import CostEstimator
        estimator = CostEstimator()
        prices = estimator.get_all_prices()
        assert "gpt-4o" in prices
        assert "claude-3-opus-20240229" in prices
        assert "qwen-turbo" in prices

    def test_int007_cost_estimator_estimate_method(self):
        from pstds.llm.cost_estimator import CostEstimator
        estimator = CostEstimator()
        estimate = estimator.estimate(prompt="Test" * 100, model="gpt-4o")
        assert "estimated_tokens" in estimate and "estimated_cost_usd" in estimate

    def test_int008_fallback_data_source_switching(self):
        from pstds.data.fallback import FallbackManager, DataQualityReport
        import asyncio
        
        # 创建模拟的 TemporalContext
        ctx = TemporalContext.for_live(date(2024, 1, 2))
        
        # 创建模拟的主适配器（会失败）
        primary_mock = Mock()
        primary_mock.get_ohlcv = Mock(side_effect=Exception("Primary failed"))
        
        # 创建模拟的备用适配器（会成功）
        import pandas as pd
        fallback_mock = Mock()
        fallback_mock.name = "local_csv"
        fallback_mock.get_ohlcv = Mock(return_value=pd.DataFrame({"close": [100.0]}))
        
        report = DataQualityReport(score=80.0)
        manager = FallbackManager(
            primary_adapters=[primary_mock], 
            fallback_adapters=[fallback_mock], 
            report=report
        )
        
        # 运行异步方法来触发降级逻辑
        async def run_test():
            result = await manager.get_ohlcv(
                symbol="AAPL",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 5),
                interval="1d",
                ctx=ctx
            )
            return result
        
        result = asyncio.run(run_test())
        
        # 验证降级被触发
        assert len(manager.get_report().fallbacks_used) > 0
        assert "local_csv" in manager.get_report().fallbacks_used
