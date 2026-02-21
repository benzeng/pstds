# tests/conftest.py
import pytest
import json
from datetime import date
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def live_ctx_2024_01_02():
    """AAPL 前视偏差回归测试标准上下文"""
    from pstds.temporal.context import TemporalContext
    return TemporalContext.for_live(date(2024, 1, 2))


@pytest.fixture
def backtest_ctx_2024_01_02():
    from pstds.temporal.context import TemporalContext
    return TemporalContext.for_backtest(date(2024, 1, 2))


@pytest.fixture
def live_ctx_today():
    from pstds.temporal.context import TemporalContext
    from datetime import date
    return TemporalContext.for_live(date.today())


@pytest.fixture
def mixed_news_fixture():
    """含未来新闻的测试数据：5条合规 + 3条未来"""
    return json.loads((FIXTURES / "news/mixed_dates.json").read_text())


@pytest.fixture
def valid_decision_json():
    return json.loads((FIXTURES / "llm_responses/valid_trade_decision.json").read_text())
