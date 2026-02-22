# web/pages/06_portfolio.py
# 持仓管理 - Phase 6 Task 6 (P6-T6)

import streamlit as st
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 页面配置
st.set_page_config(
    page_title="持仓管理",
    page_icon="💼",
    layout="wide",
)

st.title("💼 持仓管理")
st.markdown("---")


# --- 持仓概览 ---
st.header("持仓概览", divider="blue")

# 模拟持仓数据
positions = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "shares": 100,
        "avg_cost": 175.50,
        "current_price": 182.30,
        "market_value": 18230.0,
        "unrealized_pnl": 680.0,
        "unrealized_pnl_pct": 3.87,
        "entry_date": "2024-01-15",
    },
    {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "shares": 50,
        "avg_cost": 135.00,
        "current_price": 138.20,
        "market_value": 6910.0,
        "unrealized_pnl": 165.0,
        "unrealized_pnl_pct": 2.44,
        "entry_date": "2024-01-10",
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "shares": 200,
        "avg_cost": 380.00,
        "current_price": 375.50,
        "market_value": 75100.0,
        "unrealized_pnl": -900.0,
        "unrealized_pnl_pct": -1.18,
        "entry_date": "2023-11-20",
    },
]

if not positions:
    st.info("当前没有持仓")
else:
    # 统计摘要
    total_value = sum(p["market_value"] for p in positions)
    total_cost = sum(p["shares"] * p["avg_cost"] for p in positions)
    total_pnl = sum(p["unrealized_pnl"] for p in positions)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("持仓数量", len(positions))
        st.metric("总市值", f"${total_value:,.2f}")
    with col2:
        st.metric("总成本", f"${total_cost:,.2f}")
        st.metric("未实现盈亏", f"${total_pnl:,.2f}")
    with col3:
        st.write(f"总收益率: {total_pnl / total_cost * 100:.1f}%")

    st.markdown("---")


    # --- 持仓列表 ---
    st.header("持仓详情", divider="blue")

    for pos in positions:
        with st.expander(f"{pos['symbol']} - {pos['name']} ({pos['shares']} 股)", expanded=False):
            # 基本信息
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"**持仓数**: {pos['shares']}")
                st.write(f"**平均成本**: ${pos['avg_cost']:.2f}")
            with col2:
                st.write(f"**当前价格**: ${pos['current_price']:.2f}")
                st.write(f"**市值**: ${pos['market_value']:,.2f}")
            with col3:
                pnl_color = "normal" if pos['unrealized_pnl'] >= 0 else "inverse"
                st.metric("未实现盈亏", f"${pos['unrealized_pnl']:,.2f}", delta=None, delta_color=pnl_color)
                st.write(f"收益率: {pos['unrealized_pnl_pct']:.2f}%")
            with col4:
                if st.button("📊 查看详情", key=f"detail_{pos['symbol']}"):
                    st.info(f"查看 {pos['symbol']} 详情")

            # 入场时间
            st.write(f"**入场日期**: {pos['entry_date']}")

            st.markdown("---")

    # --- 操作 ---
    st.header("操作", divider="blue")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("➕ 加仓", type="primary", width="stretch"):
            st.info("加仓功能（实际实现需要输入数量和价格）")

    with col2:
        if st.button("➖ 减仓", width="stretch"):
            st.info("减仓功能（实际实现需要输入数量）")

    with col3:
        if st.button("🔄 全部平仓", width="stretch"):
            st.warning("全部平仓功能（实际实现需要确认）")

    st.markdown("---")


    # --- 风险分析 ---
    st.header("风险分析", divider="blue")

    # 集中度风险
    symbols = [p["symbol"] for p in positions]
    sector_distribution = {
        "科技": ["AAPL", "MSFT"],
        "其他": ["GOOGL"],
    }

    st.subheader("行业分布")
    for sector, symbols in sector_distribution.items():
        st.write(f"**{sector}**: {', '.join(symbols)}")

    st.markdown("---")

    # 集中度分析
    st.subheader("集中度风险")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("最大持仓占比", "50.0% (MSFT)")
        st.metric("前3大持仓", "MSFT, AAPL, GOOGL")
    with col2:
        st.warning("持仓相对集中，建议适当分散")

    st.markdown("---")

    # 持仓建议
    st.subheader("持仓建议")

    if len(positions) > 3:
        st.info("持仓数量较多，建议审查各持仓的基本面和趋势")
    elif total_pnl < 0:
        st.warning("存在亏损持仓，建议评估止损策略")
    else:
        st.success("持仓表现良好，继续保持")


# --- 底部信息 ---
st.markdown("---")

st.caption("""
**重要免责声明：**

本持仓管理页为 PSTDS 系统的一部分。所有持仓数据仅供参考，
不构成任何投资建议。投资有风险，入市须谨慎。

- 持仓数据可能存在延迟或误差
- 实际交易请以券商确认的价格为准
- 开发者不对基于本页做出的任何决策承担责任

© 2026 PSTDS - 个人专用股票交易决策系统
""")
