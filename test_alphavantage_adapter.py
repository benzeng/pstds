#!/usr/bin/env python3
# AlphaVantageAdapter 测试脚本

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime, UTC
import pandas as pd
from pstds.temporal.context import TemporalContext
from pstds.data.adapters.alphavantage_adapter import AlphaVantageAdapter

def test_alphavantage_ohlcv():
    """测试 AlphaVantageAdapter 的 OHLCV 数据获取"""
    print("\n=== Testing OHLCV Data Retrieval ===")

    # Initialize adapter
    try:
        adapter = AlphaVantageAdapter()
        print("AlphaVantageAdapter initialized successfully")
    except ValueError as e:
        print(f"Failed to initialize AlphaVantageAdapter: {e}")
        print("Please set ALPHA_VANTAGE_API_KEY environment variable")
        return

    # Create TemporalContext (LIVE mode)
    ctx = TemporalContext.for_live(date.today())

    # Test stock symbols
    symbols = ["AAPL", "MSFT", "TSLA"]

    for symbol in symbols:
        print(f"\nTesting symbol: {symbol}")
        try:
            # Get daily data for past 30 days (AlphaVantage has rate limits)
            end_date = date.today()
            start_date = date(end_date.year, end_date.month - 1, end_date.day)  # Past month

            df = adapter.get_ohlcv(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval="1d",
                ctx=ctx
            )

            if not df.empty:
                print(f"SUCCESS: Got {len(df)} OHLCV records")
                print(f"Date range: {df['date'].min()} to {df['date'].max()}")
                print(f"Columns: {list(df.columns)}")
                print(f"Latest 3 records:")
                print(df.tail(3).to_string(index=False))
            else:
                print("No data retrieved")

        except Exception as e:
            print(f"ERROR getting {symbol} OHLCV: {e}")

def test_alphavantage_fundamentals():
    """测试 AlphaVantageAdapter 的基本面数据获取"""
    print("\n=== Testing Fundamentals Data Retrieval ===")

    # Initialize adapter
    try:
        adapter = AlphaVantageAdapter()
    except ValueError as e:
        print(f"Failed to initialize AlphaVantageAdapter: {e}")
        return

    # Create TemporalContext (LIVE mode)
    ctx = TemporalContext.for_live(date.today())

    # Test stock symbols
    symbols = ["AAPL", "MSFT", "GOOGL"]

    for symbol in symbols:
        print(f"\nTesting symbol: {symbol}")
        try:
            fundamentals = adapter.get_fundamentals(
                symbol=symbol,
                as_of_date=date.today(),
                ctx=ctx
            )

            print(f"SUCCESS: Got fundamentals data:")
            for key, value in fundamentals.items():
                if value is not None:
                    print(f"  {key}: {value}")

        except Exception as e:
            print(f"ERROR getting {symbol} fundamentals: {e}")

def test_alphavantage_news():
    """测试 AlphaVantageAdapter 的新闻数据获取"""
    print("\n=== Testing News Data Retrieval ===")

    # Initialize adapter
    try:
        adapter = AlphaVantageAdapter()
    except ValueError as e:
        print(f"Failed to initialize AlphaVantageAdapter: {e}")
        return

    # Create TemporalContext (LIVE mode)
    ctx = TemporalContext.for_live(date.today())

    # Test stock symbols
    symbols = ["AAPL", "TSLA"]

    for symbol in symbols:
        print(f"\nTesting symbol: {symbol}")
        try:
            news_items = adapter.get_news(
                symbol=symbol,
                days_back=7,  # Past 7 days
                ctx=ctx
            )

            if news_items:
                print(f"SUCCESS: Got {len(news_items)} news items")
                for i, news in enumerate(news_items[:3]):  # Show first 3
                    print(f"\nNews {i+1}:")
                    print(f"  Title: {news.title}")
                    print(f"  Published: {news.published_at}")
                    print(f"  Source: {news.source}")
                    print(f"  Relevance: {news.relevance_score}")
            else:
                print("No news data retrieved")

        except Exception as e:
            print(f"ERROR getting {symbol} news: {e}")

def test_adapter_capabilities():
    """测试适配器能力"""
    print("\n=== Testing Adapter Capabilities ===")

    try:
        adapter = AlphaVantageAdapter()
    except ValueError as e:
        print(f"Failed to initialize AlphaVantageAdapter: {e}")
        return

    test_symbols = ["AAPL", "MSFT", "GOOGL"]

    for symbol in test_symbols:
        print(f"\nTesting symbol: {symbol}")
        try:
            # Check availability
            available = adapter.is_available(symbol)
            print(f"  Available: {available}")

            # Get market type
            market_type = adapter.get_market_type(symbol)
            print(f"  Market type: {market_type}")

        except Exception as e:
            print(f"  ERROR: {e}")

if __name__ == "__main__":
    print("Starting AlphaVantageAdapter Test")
    print(f"Current time: {datetime.now(UTC)}")

    # Check if API key is available
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        print("\nWARNING: ALPHA_VANTAGE_API_KEY environment variable not set")
        print("AlphaVantageAdapter tests will fail without a valid API key")
        print("Get a free API key from: https://www.alphavantage.co/support/#api-key")

    try:
        # 测试适配器能力
        test_adapter_capabilities()

        # 测试 OHLCV 数据
        test_alphavantage_ohlcv()

        # 测试基本面数据
        test_alphavantage_fundamentals()

        # 测试新闻数据
        test_alphavantage_news()

        print("\nAll tests completed!")

    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()