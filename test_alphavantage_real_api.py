#!/usr/bin/env python3
# AlphaVantageAdapter 真实 API 测试

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime, UTC
import pandas as pd
from pstds.temporal.context import TemporalContext
from pstds.data.adapters import AlphaVantageAdapter

def test_real_ohlcv_data():
    """测试真实 OHLCV 数据"""
    print("=== Testing Real OHLCV Data ===")

    try:
        adapter = AlphaVantageAdapter()
        ctx = TemporalContext.for_live(date.today())

        # Get data for the past few days
        end_date = date.today()
        start_date = date(end_date.year, end_date.month, max(1, end_date.day - 10))

        print(f"Fetching AAPL data from {start_date} to {end_date}")

        df = adapter.get_ohlcv(
            symbol="AAPL",
            start_date=start_date,
            end_date=end_date,
            interval="1d",
            ctx=ctx
        )

        if not df.empty:
            print(f"[SUCCESS] Got {len(df)} real OHLCV records")
            print(f"Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"Latest close: ${df['close'].iloc[-1]:.2f}")
            print(f"Data source: {df['data_source'].iloc[0]}")
            print(f"Sample data:")
            print(df.tail(3).to_string(index=False))
            return True
        else:
            print("[WARNING] No OHLCV data returned")
            return False

    except Exception as e:
        print(f"[ERROR] OHLCV test failed: {e}")
        return False

def test_real_fundamentals_data():
    """测试真实基本面数据"""
    print("\n=== Testing Real Fundamentals Data ===")

    try:
        adapter = AlphaVantageAdapter()
        ctx = TemporalContext.for_live(date.today())

        fundamentals = adapter.get_fundamentals(
            symbol="AAPL",
            as_of_date=date.today(),
            ctx=ctx
        )

        print("[INFO] Fundamentals retrieved:")
        real_data_found = False
        for key, value in fundamentals.items():
            if value is not None and value != '' and not (isinstance(value, float) and value == 0.0):
                print(f"  {key}: {value}")
                real_data_found = True

        if real_data_found:
            print("[SUCCESS] Real fundamentals data found")
            return True
        else:
            print("[WARNING] No real fundamentals data found")
            return False

    except Exception as e:
        print(f"[ERROR] Fundamentals test failed: {e}")
        return False

def test_real_news_data():
    """测试真实新闻数据"""
    print("\n=== Testing Real News Data ===")

    try:
        adapter = AlphaVantageAdapter()
        ctx = TemporalContext.for_live(date.today())

        news_items = adapter.get_news(
            symbol="AAPL",
            days_back=7,
            ctx=ctx
        )

        if news_items:
            print(f"[SUCCESS] Got {len(news_items)} real news items")
            for i, news in enumerate(news_items[:3]):
                print(f"\nNews {i+1}:")
                print(f"  Title: {news.title}")
                print(f"  Source: {news.source}")
                print(f"  Published: {news.published_at}")
                print(f"  Relevance: {news.relevance_score}")
            return True
        else:
            print("[WARNING] No news data returned")
            return False

    except Exception as e:
        print(f"[ERROR] News test failed: {e}")
        return False

def main():
    print("Starting AlphaVantageAdapter Real API Test")
    print(f"Current time: {datetime.now(UTC)}")
    print(f"API Key: {os.getenv('ALPHA_VANTAGE_API_KEY', 'Not set')[:8]}...")
    print("=" * 60)

    results = {
        'ohlcv': False,
        'fundamentals': False,
        'news': False
    }

    try:
        # Test OHLCV data
        results['ohlcv'] = test_real_ohlcv_data()

        # Test fundamentals data
        results['fundamentals'] = test_real_fundamentals_data()

        # Test news data
        results['news'] = test_real_news_data()

        # Summary
        print("\n" + "=" * 60)
        print("REAL API TEST SUMMARY")
        print("=" * 60)

        all_passed = True
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status} {test_name.upper()}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 60)
        if all_passed:
            print("[SUCCESS] All real API tests passed!")
        else:
            print("[INFO] Some tests failed or returned no data")
            print("This might be due to API rate limits or data availability")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()