#!/usr/bin/env python3
# AlphaVantageAdapter 模拟测试脚本

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime, UTC
import pandas as pd
from unittest.mock import patch, MagicMock
from pstds.temporal.context import TemporalContext
from pstds.data.adapters.alphavantage_adapter import AlphaVantageAdapter

def test_alphavantage_adapter_structure():
    """测试 AlphaVantageAdapter 的结构和接口"""
    print("\n=== Testing AlphaVantageAdapter Structure ===")

    # Test adapter can be imported
    try:
        from pstds.data.adapters.alphavantage_adapter import AlphaVantageAdapter
        print("[OK] AlphaVantageAdapter imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import AlphaVantageAdapter: {e}")
        return False

    # Test adapter has required methods
    required_methods = ['get_ohlcv', 'get_fundamentals', 'get_news', 'is_available', 'get_market_type']

    # Create mock adapter (we'll patch the API calls)
    with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
        try:
            adapter = AlphaVantageAdapter()
            print("[OK] AlphaVantageAdapter initialized with mock API key")
        except Exception as e:
            print(f"[FAIL] Failed to initialize AlphaVantageAdapter: {e}")
            return False

        # Check if all required methods exist
        for method_name in required_methods:
            if hasattr(adapter, method_name):
                print(f"[OK] Method {method_name} exists")
            else:
                print(f"[FAIL] Method {method_name} missing")
                return False

        # Test method signatures
        ctx = TemporalContext.for_live(date.today())

        # Test get_market_type
        try:
            market_type = adapter.get_market_type("AAPL")
            print(f"[OK] get_market_type returns: {market_type}")
        except Exception as e:
            print(f"[FAIL] get_market_type failed: {e}")
            return False

        return True

def test_alphavantage_ohlcv_mock():
    """测试 OHLCV 方法的模拟响应"""
    print("\n=== Testing OHLCV with Mock Data ===")

    with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
        adapter = AlphaVantageAdapter()
        ctx = TemporalContext.for_live(date.today())

        # Mock the TimeSeries response
        mock_data = pd.DataFrame({
            '1. open': [150.0, 151.0],
            '2. high': [152.0, 153.0],
            '3. low': [149.0, 150.0],
            '4. close': [151.0, 152.0],
            '5. adjusted close': [151.0, 152.0],
            '6. volume': [1000000, 1100000],
            'date': pd.date_range(end=date.today(), periods=2, freq='D')
        }).set_index('date')

        with patch.object(adapter.ts, 'get_daily_adjusted', return_value=(mock_data, {})):
            try:
                df = adapter.get_ohlcv(
                    symbol="AAPL",
                    start_date=date.today() - pd.Timedelta(days=7),
                    end_date=date.today(),
                    interval="1d",
                    ctx=ctx
                )

                if not df.empty:
                    print(f"[OK] Mock OHLCV test successful, got {len(df)} records")
                    print(f"  Columns: {list(df.columns)}")
                    print(f"  Sample data:\n{df.head()}")
                else:
                    print("[FAIL] Mock OHLCV returned empty data")

            except Exception as e:
                print(f"[FAIL] Mock OHLCV test failed: {e}")

def test_alphavantage_fundamentals_mock():
    """测试基本面方法的模拟响应"""
    print("\n=== Testing Fundamentals with Mock Data ===")

    with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
        adapter = AlphaVantageAdapter()
        ctx = TemporalContext.for_live(date.today())

        # Mock the FundamentalData response
        mock_data = pd.DataFrame({
            'PERatio': [25.0],
            'PriceToBookRatio': [5.0],
            'ReturnOnEquityQuarterly': [0.15],
            'MarketCapitalization': [2000000000000],
            'NetIncome': [95000000000],
            'LatestQuarter': ['2024-03-31']
        })

        with patch.object(adapter.fd, 'get_company_overview', return_value=(mock_data, {})):
            try:
                fundamentals = adapter.get_fundamentals(
                    symbol="AAPL",
                    as_of_date=date.today(),
                    ctx=ctx
                )

                print(f"[OK] Mock fundamentals test successful")
                for key, value in fundamentals.items():
                    if value is not None:
                        print(f"  {key}: {value}")

            except Exception as e:
                print(f"[FAIL] Mock fundamentals test failed: {e}")

def test_alphavantage_news_mock():
    """测试新闻方法的模拟响应"""
    print("\n=== Testing News with Mock Data ===")

    with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
        adapter = AlphaVantageAdapter()
        ctx = TemporalContext.for_live(date.today())

        # Mock the news API response
        mock_response = {
            'feed': [
                {
                    'title': 'Apple Reports Strong Q4 Results',
                    'summary': 'Apple Inc. reported strong quarterly results with record revenue.',
                    'source': 'MarketWatch',
                    'url': 'https://example.com/news/1',
                    'time_published': '20241201T100000',
                    'ticker_sentiment': [
                        {
                            'ticker': 'AAPL',
                            'ticker_sentiment_score': 0.8
                        }
                    ]
                }
            ]
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status.return_value = None

            try:
                news_items = adapter.get_news(
                    symbol="AAPL",
                    days_back=7,
                    ctx=ctx
                )

                if news_items:
                    print(f"[OK] Mock news test successful, got {len(news_items)} items")
                    for i, news in enumerate(news_items[:1]):
                        print(f"  News {i+1}:")
                        print(f"    Title: {news.title}")
                        print(f"    Source: {news.source}")
                        print(f"    Relevance: {news.relevance_score}")
                else:
                    print("[FAIL] Mock news returned empty data")

            except Exception as e:
                print(f"[FAIL] Mock news test failed: {e}")

if __name__ == "__main__":
    print("Starting AlphaVantageAdapter Mock Test")
    print(f"Current time: {datetime.now(UTC)}")

    try:
        # 测试适配器结构
        success = test_alphavantage_adapter_structure()

        if success:
            # 测试 OHLCV 数据
            test_alphavantage_ohlcv_mock()

            # 测试基本面数据
            test_alphavantage_fundamentals_mock()

            # 测试新闻数据
            test_alphavantage_news_mock()

        print("\nMock tests completed!")

    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()