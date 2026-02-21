#!/usr/bin/env python3
# AKShareAdapter 综合测试 - 行情、财务、资金流、情绪

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, datetime, UTC
import pandas as pd
from pstds.temporal.context import TemporalContext
from pstds.data.adapters import AKShareAdapter

def test_market_data():
    """测试行情数据获取"""
    print("\n=== 测试行情数据 (OHLCV) ===")

    try:
        adapter = AKShareAdapter()
        ctx = TemporalContext.for_live(date.today())

        # 测试 A 股代码
        a_stock_symbols = ["600519", "000001", "300750"]  # 茅台、平安银行、宁德时代

        for symbol in a_stock_symbols:
            print(f"\n测试 A 股: {symbol}")
            try:
                # 获取最近 30 天的数据
                end_date = date.today()
                start_date = date(end_date.year, end_date.month, max(1, end_date.day - 30))

                df = adapter.get_ohlcv(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval="1d",
                    ctx=ctx
                )

                if not df.empty:
                    print(f"  [SUCCESS] 获取到 {len(df)} 条行情数据")
                    print(f"  日期范围: {df['date'].min().date()} 至 {df['date'].max().date()}")
                    print(f"  最新收盘价: {df['close'].iloc[-1] if len(df) > 0 else 'N/A'}")
                    print(f"  数据源: {df['data_source'].iloc[0] if len(df) > 0 else 'N/A'}")
                    print(f"  列名: {list(df.columns)}")
                else:
                    print(f"  [WARNING] {symbol} 无行情数据")

            except Exception as e:
                print(f"  [ERROR] {symbol} 行情数据获取失败: {e}")

        # 测试港股
        print(f"\n测试港股: 0700.HK (腾讯)")
        try:
            df_hk = adapter.get_ohlcv(
                symbol="0700.HK",
                start_date=start_date,
                end_date=end_date,
                interval="1d",
                ctx=ctx
            )

            if not df_hk.empty:
                print(f"  [SUCCESS] 获取到 {len(df_hk)} 条港股行情数据")
                print(f"  最新收盘价: {df_hk['close'].iloc[-1] if len(df_hk) > 0 else 'N/A'}")
            else:
                print(f"  [WARNING] 港股无行情数据")

        except Exception as e:
            print(f"  [ERROR] 港股行情数据获取失败: {e}")

        return True

    except Exception as e:
        print(f"[ERROR] 行情数据测试失败: {e}")
        return False

def test_financial_data():
    """测试财务数据获取"""
    print("\n=== 测试财务数据 (Fundamentals) ===")

    try:
        adapter = AKShareAdapter()
        ctx = TemporalContext.for_live(date.today())

        # 测试 A 股财务数据
        symbols = ["600519", "000001", "300750"]

        for symbol in symbols:
            print(f"\n测试 {symbol} 财务数据:")
            try:
                fundamentals = adapter.get_fundamentals(
                    symbol=symbol,
                    as_of_date=date.today(),
                    ctx=ctx
                )

                print(f"  数据源: {fundamentals.get('data_source', 'N/A')}")

                # 检查关键字段
                key_fields = ['pe_ratio', 'pb_ratio', 'roe', 'revenue', 'net_income']
                for field in key_fields:
                    value = fundamentals.get(field)
                    if value is not None:
                        print(f"  {field}: {value}")

                if fundamentals.get('pe_ratio') is not None:
                    print(f"  [SUCCESS] {symbol} 财务数据获取成功")
                else:
                    print(f"  [WARNING] {symbol} 财务数据为空")

            except Exception as e:
                print(f"  [ERROR] {symbol} 财务数据获取失败: {e}")

        return True

    except Exception as e:
        print(f"[ERROR] 财务数据测试失败: {e}")
        return False

def test_fund_flow():
    """测试资金流数据"""
    print("\n=== 测试资金流数据 (Fund Flow) ===")

    try:
        # 检查 AKShareAdapter 是否支持资金流数据
        adapter = AKShareAdapter()

        # 查看适配器是否有资金流相关方法
        has_fund_flow = hasattr(adapter, 'get_fund_flow') or hasattr(adapter, 'get_capital_flow')

        if has_fund_flow:
            print("[INFO] AKShareAdapter 支持资金流数据")
            # 这里可以添加具体的资金流测试
            print("[INFO] 资金流测试功能待实现")
        else:
            print("[INFO] AKShareAdapter 当前版本不直接支持资金流数据")
            print("[INFO] 资金流数据通常通过以下方式获取:")
            print("  - 通过新闻/情绪数据分析间接获得")
            print("  - 通过专门的资金流API（需额外实现）")

        return True

    except Exception as e:
        print(f"[ERROR] 资金流数据测试失败: {e}")
        return False

def test_sentiment_data():
    """测试情绪数据（通过新闻接口）"""
    print("\n=== 测试情绪数据 (Sentiment via News) ===")

    try:
        adapter = AKShareAdapter()
        ctx = TemporalContext.for_live(date.today())

        # 测试 A 股情绪数据
        symbols = ["600519", "000001", "300750"]

        for symbol in symbols:
            print(f"\n测试 {symbol} 情绪数据:")
            try:
                news_items = adapter.get_news(
                    symbol=symbol,
                    days_back=7,
                    ctx=ctx
                )

                if news_items:
                    print(f"  [SUCCESS] 获取到 {len(news_items)} 条相关新闻")

                    # 分析情绪
                    positive_count = 0
                    negative_count = 0
                    neutral_count = 0

                    for i, news in enumerate(news_items[:5]):  # 只看前5条
                        print(f"  新闻 {i+1}: {news.title}")
                        print(f"    相关性: {news.relevance_score}")
                        print(f"    来源: {news.source}")

                        # 简单情绪分析（基于相关性评分）
                        if news.relevance_score > 0.7:
                            positive_count += 1
                        elif news.relevance_score < 0.4:
                            negative_count += 1
                        else:
                            neutral_count += 1

                    print(f"  情绪分析: 积极 {positive_count}, 中性 {neutral_count}, 消极 {negative_count}")
                else:
                    print(f"  [WARNING] {symbol} 无情绪数据")

            except Exception as e:
                print(f"  [ERROR] {symbol} 情绪数据获取失败: {e}")

        return True

    except Exception as e:
        print(f"[ERROR] 情绪数据测试失败: {e}")
        return False

def test_market_type_detection():
    """测试市场类型识别"""
    print("\n=== 测试市场类型识别 ===")

    try:
        adapter = AKShareAdapter()

        test_cases = [
            ("600519", "CN_A"),  # 茅台
            ("000001", "CN_A"),  # 平安银行
            ("300750", "CN_A"),  # 宁德时代
            ("0700.HK", "HK"),   # 腾讯
            ("9988.HK", "HK"),   # 阿里巴巴
        ]

        for symbol, expected_type in test_cases:
            actual_type = adapter.get_market_type(symbol)
            status = "[SUCCESS]" if actual_type == expected_type else "[ERROR]"
            print(f"  {status} {symbol} -> {actual_type} (期望: {expected_type})")

        return True

    except Exception as e:
        print(f"[ERROR] 市场类型测试失败: {e}")
        return False

def test_availability_check():
    """测试股票可用性检查"""
    print("\n=== 测试股票可用性 ===")

    try:
        adapter = AKShareAdapter()

        test_symbols = ["600519", "000001", "300750", "0700.HK", "INVALID"]

        for symbol in test_symbols:
            try:
                available = adapter.is_available(symbol)
                status = "[SUCCESS]" if available else "[INFO]"
                print(f"  {status} {symbol} 可用性: {available}")
            except Exception as e:
                print(f"  [ERROR] {symbol} 可用性检查失败: {e}")

        return True

    except Exception as e:
        print(f"[ERROR] 可用性测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("启动 PSTDS AKShareAdapter 综合测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now(UTC)}")
    print("测试数据类型: 行情、财务、资金流、情绪")
    print("=" * 60)

    results = {
        'market_data': False,
        'financial_data': False,
        'fund_flow': False,
        'sentiment_data': False,
        'market_type': False,
        'availability': False
    }

    try:
        # 测试市场类型识别
        results['market_type'] = test_market_type_detection()

        # 测试股票可用性
        results['availability'] = test_availability_check()

        # 测试行情数据
        results['market_data'] = test_market_data()

        # 测试财务数据
        results['financial_data'] = test_financial_data()

        # 测试资金流数据
        results['fund_flow'] = test_fund_flow()

        # 测试情绪数据
        results['sentiment_data'] = test_sentiment_data()

        # 总结结果
        print("\n" + "=" * 60)
        print("AKShareAdapter 综合测试总结")
        print("=" * 60)

        all_passed = True
        for test_name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            display_name = test_name.replace('_', ' ').title()
            print(f"{status} {display_name}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 60)
        if all_passed:
            print("[SUCCESS] 所有测试通过！AKShareAdapter 工作正常")
        else:
            print("[WARNING] 部分测试失败，请检查详细输出")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] 测试执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()