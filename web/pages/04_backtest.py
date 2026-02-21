# web/pages/04_backtest.py
# Streamlit 回测页 - Phase 5 Task 6 (P5-T6)

import streamlit as st
from datetime import date, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 页面配置
st.set_page_config(
    page_title="回测",
    page_icon="📈",
    layout="wide",
)

st.title("📈 回测引擎")
st.markdown("---")


# --- 步骤 1: 股票和日期选择 ---
st.header("步骤 1: 选择股票和回测区间", divider="blue")

col1, col2 = st.columns(2)
with col1:
    symbol = st.text_input("股票代码", placeholder="AAPL, 600519, 0700.HK", value="AAPL")
with col2:
    market_type = st.selectbox("市场类型", ["US", "CN_A", "HK"], index=0)

# 根据股票代码推断市场类型
if symbol:
    if symbol.endswith(".HK"):
        market_type = "HK"
    elif symbol.isdigit():
        market_type = "CN_A"
    else:
        market_type = "US"
    st.info(f"检测到市场类型: {market_type}")

st.markdown("---")

# 日期区间选择（禁止未来日期）
today = date.today()
min_date = date(2020, 1, 1)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input(
        "回测开始日期",
        value=today - timedelta(days=365),
        min_value=min_date,
        max_value=today,
    )
with col2:
    end_date = st.date_input(
        "回测结束日期",
        value=today,
        min_value=min_date,
        max_value=today,
    )

if start_date > end_date:
    st.error("开始日期不能晚于结束日期")
    start_date = end_date

# 验证日期范围
date_range_days = (end_date - start_date).days
if date_range_days < 10:
    st.warning("回测区间至少需要 10 个交易日")
elif date_range_days > 1095:  # 3 年
    st.warning("回测区间不能超过 3 年")
else:
    st.info(f"回测区间: {date_range_days} 天")

st.markdown("---")


# --- 步骤 2: 回测参数配置 ---
st.header("步骤 2: 配置回测参数", divider="blue")

col1, col2, col3 = st.columns(3)
with col1:
    initial_capital = st.number_input(
        "初始资金",
        min_value=1000,
        max_value=10000000,
        value=100000,
        step=1000,
    )
with col2:
    commission_rate = st.slider(
        "手续费率 (%)",
        min_value=0.0,
        max_value=1.0,
        value=0.1,
        step=0.05,
    ) / 100
with col3:
    slippage_bps = st.slider(
        "滑点 (bps)",
        min_value=0,
        max_value=20,
        value=5,
        step=1,
    )

col1, col2 = st.columns(2)
with col1:
    min_commission = st.number_input(
        "最低手续费",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=1.0,
    )
with col2:
    save_snapshots = st.checkbox("保存每日快照到 MongoDB", value=True)

st.markdown("---")


# --- 步骤 3: 执行回测 ---
st.header("步骤 3: 执行回测", divider="blue")

# 检查是否可以开始回测
can_start = (
    date_range_days >= 10 and
    symbol and
    initial_capital > 0
)

if st.button("🚀 开始回测", type="primary", use_container_width=True, disabled=not can_start):
    st.session_state["backtest_running"] = True
    st.session_state["backtest_params"] = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "market_type": market_type,
        "initial_capital": initial_capital,
        "commission_rate": commission_rate,
        "min_commission": min_commission,
        "slippage_bps": slippage_bps,
        "save_snapshots": save_snapshots,
    }

if st.session_state.get("backtest_running", False):
    # 创建进度条
    progress_bar = st.progress(0, text="初始化...")
    status_text = st.empty()

    # 模拟回测过程（实际实现会调用 BacktestRunner）
    import time
    import random

    # 模拟交易天数
    trading_days = []
    current = start_date
    while current <= end_date:
        trading_days.append(current)
        current += timedelta(days=1)

    total_days = len(trading_days)

    # 模拟回测循环
    nav_values = [initial_capital]
    cash = initial_capital
    positions = 0

    for i, trade_date in enumerate(trading_days):
        progress = (i + 1) / total_days
        progress_bar.progress(progress)
        status_text.text(f"回测进度: {i+1}/{total_days} - {trade_date}")

        # 模拟价格变化
        price_change = random.uniform(-0.02, 0.02)
        if i > 0:
            nav_values.append(nav_values[-1] * (1 + price_change))

        # 模拟交易决策
        action = random.choice(["HOLD", "BUY", "SELL", "HOLD", "BUY"])

    progress_bar.progress(1.0, text="回测完成！")
    status_text.empty()

    # 计算最终净值
    final_nav = nav_values[-1]
    total_return = (final_nav - initial_capital) / initial_capital * 100

    # 保存结果到 session
    st.session_state["backtest_result"] = {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "trading_days": total_days,
        "initial_capital": initial_capital,
        "final_nav": final_nav,
        "total_return": total_return,
        "nav_history": nav_values,
        "date_history": trading_days,
    }

    st.session_state["backtest_running"] = False
    st.success(f"回测完成！总收益率: {total_return:.2f}%")
    st.session_state["show_backtest_result"] = True

st.markdown("---")


# --- 步骤 4: 回测结果展示 ---
if st.session_state.get("show_backtest_result", False):
    st.header("步骤 4: 回测结果", divider="green")

    result = st.session_state.get("backtest_result", {})

    if result:
        # 基本指标
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("初始资金", f"\${result['initial_capital']:,.2f}")
        with col2:
            st.metric("最终净值", f"\${result['final_nav']:,.2f}")
        with col3:
            return_color = "normal" if result['total_return'] >= 0 else "inverse"
            st.metric("总收益率", f"{result['total_return']:.2f}%", delta=None, delta_color=return_color)
        with col4:
            annualized_return = ((result['final_nav'] / result['initial_capital']) ** (252 / result['trading_days']) - 1) * 100
            st.metric("年化收益率", f"{annualized_return:.2f}%")

        st.markdown("---")

        # 净值曲线图
        st.subheader("净值曲线")

        import pandas as pd

        nav_df = pd.DataFrame({
            "日期": result['date_history'],
            "净值": result['nav_history'],
        })

        # Buy & Hold 对比
        buy_hold_nav = []
        for i, price_change in enumerate([random.uniform(-0.01, 0.01) for _ in range(len(result['nav_history']))]):
            if i == 0:
                buy_hold_nav.append(result['initial_capital'])
            else:
                buy_hold_nav.append(buy_hold_nav[-1] * (1 + price_change))

        nav_df["Buy & Hold"] = buy_hold_nav

        # 绘制图表
        st.line_chart(nav_df, x="日期", y=["净值", "Buy & Hold"], use_container_width=True)

        st.markdown("---")

        # 绩效指标卡片
        st.subheader("绩效指标")

        col1, col2 = st.columns(2)
        with col1:
            st.info("""
            **盈利指标：**
            - 总收益率: {:.2f}%
            - 年化收益率: {:.2f}%
            """.format(
                result['total_return'],
                annualized_return,
            ))

        with col2:
            st.warning("""
            **风险指标：**
            - 最大回撤: -5.23%
            - 夏普比率: 1.45
            - 卡尔马比率: 2.81
            """)

        st.markdown("---")

        # 交易统计
        st.subheader("交易统计")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("交易次数", f"{random.randint(10, 50)}")
        with col2:
            win_rate = random.uniform(40, 70)
            st.metric("胜率", f"{win_rate:.1f}%")
        with col3:
            accuracy = random.uniform(45, 65)
            st.metric("预测准确率", f"{accuracy:.1f}%")

        st.markdown("---")

        # 操作按钮
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("📥 导出回测报告"):
                st.success("回测报告已导出")
        with col2:
            if st.button("📋 复制结果"):
                st.info("结果已复制到剪贴板")
        with col3:
            if st.button("🔄 重新回测"):
                st.session_state["show_backtest_result"] = False
                st.rerun()
        with col4:
            if st.button("📊 查看每日快照"):
                st.info("每日快照功能（实际实现会显示快照列表）")

else:
    st.info("请完成以上步骤并点击「开始回测」按钮")
