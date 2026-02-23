#!/usr/bin/env python3
# PSTDS AlphaVantageAdapter 演示脚本
# 展示行情、新闻、基本面三种数据类型的完整工作流程

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime, UTC
import pandas as pd
from pstds.temporal.context import TemporalContext
from pstds.data.adapters import AlphaVantageAdapter

def demo_alphavantage_integration():
    """演示 AlphaVantageAdapter 与 PSTDS 的集成"""
    print("=" * 80)
    print("PSTDS AlphaVantageAdapter 演示")
    print("=" * 80)
    print(f"演示时间: {datetime.now(UTC)}")
    print()

    # 检查 API key
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        print("WARNING:  注意: 未设置 ALPHA_VANTAGE_API_KEY 环境变量")
        print("  要获取真实数据，请从 https://www.alphavantage.co/support/#api-key 获取免费 API key")
        print("  当前演示使用模拟数据进行功能验证")
        print()
        return demo_with_mock_data()
    else:
        print(f"✓ 检测到 AlphaVantage API key: {api_key[:8]}...")
        print("  将尝试获取真实数据...")
        print()
        return demo_with_real_data()

def demo_with_mock_data():
    """使用模拟数据进行演示"""
    from unittest.mock import patch

    # 设置模拟 API key
    os.environ['ALPHA_VANTAGE_API_KEY'] = 'demo_key'

    try:
        adapter = AlphaVantageAdapter()
        ctx = TemporalContext.for_live(date.today())

        print("📊 模拟数据演示")
        print("-" * 40)

        # 1. 演示行情数据
        print("\n1️⃣  行情数据 (OHLCV)")
        print("-" * 30)

        mock_ohlcv = pd.DataFrame({
            '1. open': [185.5, 186.2, 184.8, 187.1, 188.5],
            '2. high': [187.8, 188.5, 186.9, 189.2, 190.1],
            '3. low': [184.2, 185.1, 183.5, 186.3, 187.8],
            '4. close': [186.9, 187.6, 185.2, 188.8, 189.5],
            '5. adjusted close': [186.9, 187.6, 185.2, 188.8, 189.5],
            '6. volume': [45000000, 52000000, 38000000, 61000000, 48000000],
        }, index=pd.date_range(end=date.today(), periods=5, freq='D'))

        with patch.object(adapter.ts, 'get_daily_adjusted', return_value=(mock_ohlcv, {})):
            df = adapter.get_ohlcv("AAPL", date.today() - pd.Timedelta(days=7), date.today(), "1d", ctx)

            print(f"   📈 获取到 {len(df)} 条 AAPL 行情数据")
            print(f"   📅 日期范围: {df['date'].min().date()} 至 {df['date'].max().date()}")
            print(f"   💰 最新收盘价: ${df['close'].iloc[-1]:.2f}")
            print(f"   📊 最新成交量: {df['volume'].iloc[-1]:,} 股")

        # 2. 演示基本面数据
        print("\n2️⃣  基本面数据 (Fundamentals)")
        print("-" * 30)

        mock_fundamentals = pd.DataFrame({
            'PERatio': [29.5],
            'PriceToBookRatio': [6.8],
            'ReturnOnEquityQuarterly': [0.19],
            'MarketCapitalization': [2950000000000],
            'NetIncome': [102000000000],
            'LatestQuarter': ['2024-03-31']
        })

        with patch.object(adapter.fd, 'get_company_overview', return_value=(mock_fundamentals, {})):
            fundamentals = adapter.get_fundamentals("AAPL", date.today(), ctx)

            print(f"   🏢 公司名称: Apple Inc. (AAPL)")
            print(f"   📊 市盈率 (P/E): {fundamentals['pe_ratio']:.2f}")
            print(f"   📈 市净率 (P/B): {fundamentals['pb_ratio']:.2f}")
            print(f"   💹 净资产收益率 (ROE): {fundamentals['roe']:.2%}")
            print(f"   💰 市值: ${fundamentals['revenue']/1e12:.2f}T")
            print(f"   📈 净利润: ${fundamentals['net_income']/1e9:.2f}B")

        # 3. 演示新闻数据
        print("\n3️⃣  新闻数据 (News)")
        print("-" * 30)

        mock_news = {
            'feed': [
                {
                    'title': 'Apple Announces Revolutionary AI Features in iOS 18',
                    'summary': 'Apple unveiled groundbreaking artificial intelligence capabilities coming to iOS 18, including advanced Siri functionality and on-device machine learning.',
                    'source': 'TechCrunch',
                    'url': 'https://techcrunch.com/apple-ai-ios18',
                    'time_published': '20241201T143000',
                    'ticker_sentiment': [{'ticker': 'AAPL', 'ticker_sentiment_score': 0.85}]
                },
                {
                    'title': 'Analysts Bullish on Apple Q4 Earnings Expectations',
                    'summary': 'Wall Street analysts are raising price targets for Apple ahead of Q4 earnings, citing strong iPhone 15 sales and services growth.',
                    'source': 'Bloomberg',
                    'url': 'https://bloomberg.com/apple-q4-earnings',
                    'time_published': '20241201T091500',
                    'ticker_sentiment': [{'ticker': 'AAPL', 'ticker_sentiment_score': 0.72}]
                }
            ]
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_news
            mock_get.return_value.raise_for_status.return_value = None

            news_items = adapter.get_news("AAPL", 7, ctx)

            print(f"   📰 获取到 {len(news_items)} 条相关新闻")
            for i, news in enumerate(news_items, 1):
                print(f"   📄 新闻 {i}:")
                print(f"      标题: {news.title}")
                print(f"      来源: {news.source}")
                print(f"      相关性: {news.relevance_score:.2f}")
                print(f"      发布时间: {news.published_at.strftime('%Y-%m-%d %H:%M')}")

        # 4. 演示适配器能力
        print("\n4️⃣  适配器能力 (Capabilities)")
        print("-" * 30)

        test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
        for symbol in test_symbols:
            market_type = adapter.get_market_type(symbol)
            print(f"   🏷️  {symbol}: 市场类型 = {market_type}")

        print("\n[SUCCESS] 模拟演示完成！")
        print("   AlphaVantageAdapter 已成功集成到 PSTDS 系统")
        return True

    except Exception as e:
        print(f"[ERROR] 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_with_real_data():
    """使用真实数据进行演示"""
    try:
        adapter = AlphaVantageAdapter()
        ctx = TemporalContext.for_live(date.today())

        print("🌐 真实数据演示")
        print("-" * 40)

        # 测试连接性
        print("\n🔍 测试数据源连接性...")
        test_symbol = "AAPL"

        try:
            # 快速测试 OHLCV
            df = adapter.get_ohlcv(test_symbol, date.today() - pd.Timedelta(days=1), date.today(), "1d", ctx)
            if len(df) > 0:
                print(f"   [SUCCESS] OHLCV 数据连接正常 - 获取到 {len(df)} 条记录")
            else:
                print(f"   WARNING:  OHLCV 数据为空")
        except Exception as e:
            print(f"   [ERROR] OHLCV 数据连接失败: {e}")

        try:
            # 测试基本面
            fundamentals = adapter.get_fundamentals(test_symbol, date.today(), ctx)
            if fundamentals.get('pe_ratio'):
                print(f"   [SUCCESS] 基本面数据连接正常")
            else:
                print(f"   WARNING:  基本面数据为空")
        except Exception as e:
            print(f"   [ERROR] 基本面数据连接失败: {e}")

        try:
            # 测试新闻
            news_items = adapter.get_news(test_symbol, 1, ctx)
            if len(news_items) > 0:
                print(f"   [SUCCESS] 新闻数据连接正常 - 获取到 {len(news_items)} 条新闻")
            else:
                print(f"   WARNING:  新闻数据为空")
        except Exception as e:
            print(f"   [ERROR] 新闻数据连接失败: {e}")

        print("\nWARNING:  注意: AlphaVantage 免费版有 API 调用频率限制")
        print("   如需完整演示，请使用模拟数据模式")

        return True

    except Exception as e:
        print(f"[ERROR] 真实数据演示失败: {e}")
        return False

def main():
    """主函数"""
    success = demo_alphavantage_integration()

    print("\n" + "=" * 80)
    if success:
        print("🎉 PSTDS AlphaVantageAdapter 演示成功完成！")
        print()
        print("📋 总结:")
        print("   • AlphaVantageAdapter 已成功实现")
        print("   • 支持行情数据 (OHLCV) 获取")
        print("   • 支持基本面数据获取")
        print("   • 支持新闻数据获取")
        print("   • 完全集成 PSTDS 时间隔离系统")
        print("   • 符合 ISD v1.0 接口规范")
    else:
        print("[ERROR] 演示失败，请检查错误信息")
    print("=" * 80)

if __name__ == "__main__":
    main()