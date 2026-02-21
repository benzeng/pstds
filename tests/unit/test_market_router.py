# tests/unit/test_market_router.py
# 市场路由器测试套件 - RT-001 至 RT-008

import pytest

from pstds.data.router import MarketRouter, MarketNotSupportedError


class TestMarketRouter:
    """RT-001 至 RT-008: 市场路由测试"""

    def test_rt001_a_shanghai_stock(self):
        """RT-001: 沪市股票 (600xxx) 应路由到 CN_A"""
        result = MarketRouter.route("600519")
        assert result == "CN_A"

    def test_rt002_a_shenzhen_main(self):
        """RT-002: 深市主板 (000xxx) 应路由到 CN_A"""
        result = MarketRouter.route("000001")
        assert result == "CN_A"

    def test_rt003_a_shenzhen_chi_next(self):
        """RT-003: 创业板 (300xxx) 应路由到 CN_A"""
        result = MarketRouter.route("300750")
        assert result == "CN_A"

    def test_rt004_hk_stock(self):
        """RT-004: 港股 (xxx.HK) 应路由到 HK"""
        result = MarketRouter.route("0700.HK")
        assert result == "HK"

    def test_rt005_us_stock_single_letter(self):
        """RT-005: 美股 (单字母) 应路由到 US"""
        result = MarketRouter.route("AAPL")
        assert result == "US"

    def test_rt006_us_stock_multiple_letters(self):
        """RT-006: 美股 (多字母) 应路由到 US"""
        result = MarketRouter.route("NVDA")
        assert result == "US"

    def test_rt007_us_etf(self):
        """RT-007: 美股 ETF (SPY) 应路由到 US"""
        result = MarketRouter.route("SPY")
        assert result == "US"

    def test_rt008_invalid_symbol(self):
        """RT-008: 无效股票代码应抛出 MarketNotSupportedError"""
        with pytest.raises(MarketNotSupportedError) as exc_info:
            MarketRouter.route("INVALID@#$")

        assert "股票代码格式无法识别" in str(exc_info.value)
        assert "E009" in str(exc_info.value)

    def test_a_stock_valid_prefixes(self):
        """测试所有 A 股有效前缀"""
        valid_prefixes = ["60", "00", "30", "68", "83", "43"]
        for prefix in valid_prefixes:
            symbol = f"{prefix}0001"
            result = MarketRouter.route(symbol)
            assert result == "CN_A", f"前缀 {prefix} 应路由到 CN_A"

    def test_a_stock_invalid_prefix(self):
        """测试 A 股无效前缀"""
        invalid_prefixes = ["10", "20", "40", "50"]
        for prefix in invalid_prefixes:
            symbol = f"{prefix}0001"
            with pytest.raises(MarketNotSupportedError):
                MarketRouter.route(symbol)

    def test_hk_stock_various_lengths(self):
        """测试不同长度的港股代码"""
        hk_symbols = ["0700.HK", "9988.HK", "3690.HK"]
        for symbol in hk_symbols:
            result = MarketRouter.route(symbol)
            assert result == "HK"

    def test_us_stock_various_lengths(self):
        """测试不同长度的美股代码"""
        us_symbols = ["A", "AA", "AAPL", "GOOGL", "BRK.B"]
        for symbol in us_symbols:
            result = MarketRouter.route(symbol)
            assert result == "US"

    def test_mixed_case_us_stock(self):
        """测试大小写混合的美股代码"""
        result = MarketRouter.route("aapl")
        assert result == "US"

        result = MarketRouter.route("AAPL")
        assert result == "US"
