# web/pages/03_history.py
# 历史记录页面 - Phase 4 Task 6 (P4-T6)

import streamlit as st
from datetime import date, datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 页面配置
st.set_page_config(
    page_title="历史记录",
    page_icon="📜",
    layout="wide",
)

st.title("📜 历史分析记录")
st.markdown("---")


# 初始化 session state
if "history_data" not in st.session_state:
    # 模拟历史数据
    st.session_state["history_data"] = [
        {
            "symbol": "AAPL",
            "analysis_date": "2024-01-15",
            "action": "BUY",
            "confidence": 0.72,
            "conviction": "MEDIUM",
            "created_at": "2024-01-15T10:30:00Z",
            "cost_usd": 0.12,
            "tokens": 38000,
        },
        {
            "symbol": "AAPL",
            "analysis_date": "2024-01-16",
            "action": "HOLD",
            "confidence": 0.55,
            "conviction": "LOW",
            "created_at": "2024-01-16T10:30:00Z",
            "cost_usd": 0.10,
            "tokens": 32000,
        },
        {
            "symbol": "600519",
            "analysis_date": "2024-01-14",
            "action": "BUY",
            "confidence": 0.68,
            "conviction": "MEDIUM",
            "created_at": "2024-01-14T14:20:00Z",
            "cost_usd": 0.08,
            "tokens": 25000,
        },
        {
            "symbol": "0700.HK",
            "analysis_date": "2024-01-17",
            "action": "SELL",
            "confidence": 0.65,
            "conviction": "MEDIUM",
            "created_at": "2024-01-17T09:15:00Z",
            "cost_usd": 0.15,
            "tokens": 45000,
        },
    ]


# --- 筛选条件 ---
st.header("筛选条件", divider="blue")

col1, col2, col3, col4 = st.columns(4)

with col1:
    symbol_filter = st.text_input("股票代码", placeholder="AAPL")

with col2:
    action_filter = st.selectbox(
        "决策类型",
        ["全部", "STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL", "INSUFFICIENT_DATA"],
    )

with col3:
    date_filter_mode = st.radio(
        "日期筛选",
        ["全部", "最近7天", "最近30天", "自定义"],
        horizontal=True,
    )

with col4:
    if date_filter_mode == "自定义":
        start_date = st.date_input("开始日期", value=date.today() - timedelta(days=30))
        end_date = st.date_input("结束日期", value=date.today())
    else:
        start_date = None
        end_date = None

st.markdown("---")


# --- 应用筛选 ---
filtered_data = []

today = date.today()
seven_days_ago = today - timedelta(days=7)
thirty_days_ago = today - timedelta(days=30)

for record in st.session_state["history_data"]:
    # 股票筛选
    if symbol_filter and symbol_filter.upper() not in record["symbol"].upper():
        continue

    # 决策类型筛选
    if action_filter != "全部" and record["action"] != action_filter:
        continue

    # 日期筛选
    analysis_date = datetime.strptime(record["analysis_date"], "%Y-%m-%d").date()

    if date_filter_mode == "最近7天" and analysis_date < seven_days_ago:
        continue
    if date_filter_mode == "最近30天" and analysis_date < thirty_days_ago:
        continue
    if date_filter_mode == "自定义":
        if analysis_date < start_date or analysis_date > end_date:
            continue

    filtered_data.append(record)


# --- 历史记录列表 ---
st.header("分析记录", divider="blue")

if filtered_data:
    # 按日期降序排序
    filtered_data.sort(key=lambda x: x["created_at"], reverse=True)

    for record in filtered_data:
        # 决策类型颜色
        action_colors = {
            "STRONG_BUY": "#4caf50",
            "BUY": "#8bc34a",
            "HOLD": "#ff9800",
            "SELL": "#ff5722",
            "STRONG_SELL": "#d32f2f",
            "INSUFFICIENT_DATA": "#9e9e9e",
        }
        action_color = action_colors.get(record["action"], "#9e9e9e")

        # 决策类型标签
        action_labels = {
            "STRONG_BUY": "强烈买入",
            "BUY": "买入",
            "HOLD": "持有",
            "SELL": "卖出",
            "STRONG_SELL": "强烈卖出",
            "INSUFFICIENT_DATA": "数据不足",
        }
        action_label = action_labels.get(record["action"], record["action"])

        with st.expander(
            f"{record['symbol']} - {record['analysis_date']} - {action_label}",
            expanded=False,
        ):
            col1, col2 = st.columns(2)

            with col1:
                # 决策信息
                st.markdown(f"**决策:** <span style='color:{action_color}'>**{record['action']}**</span>", unsafe_allow_html=True)
                st.write(f"**置信度:** {record['confidence'] * 100:.1f}%")
                st.write(f"**信心度:** {record['conviction']}")
                st.write(f"**分析日期:** {record['analysis_date']}")

            with col2:
                # 成本信息
                st.write(f"**创建时间:** {record['created_at']}")
                st.write(f"**使用 Token:** {record['tokens']:,}")
                st.write(f"**成本 (USD):** ${record['cost_usd']:.4f}")

            # 操作按钮
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button("📊 查看详情", key=f"view_{record['symbol']}_{record['analysis_date']}"):
                    st.info("查看详情功能（实际实现会显示完整分析）")

            with col_btn2:
                if st.button("📥 导出", key=f"export_{record['symbol']}_{record['analysis_date']}"):
                    st.success("已导出分析报告")

            with col_btn3:
                if st.button("🗑️ 删除", key=f"delete_{record['symbol']}_{record['analysis_date']}"):
                    st.session_state["history_data"] = [
                        r for r in st.session_state["history_data"]
                        if r != record
                    ]
                    st.warning("记录已删除")
                    st.rerun()
else:
    st.info("没有符合条件的分析记录")

st.markdown("---")


# --- 统计信息 ---
st.header("统计信息", divider="blue")

# 决策类型分布
action_counts = {}
for record in st.session_state["history_data"]:
    action = record["action"]
    action_counts[action] = action_counts.get(action, 0) + 1

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("总记录数", len(st.session_state["history_data"]))
with col2:
    total_cost = sum(record["cost_usd"] for record in st.session_state["history_data"])
    st.metric("总成本 (USD)", f"${total_cost:.4f}")
with col3:
    total_tokens = sum(record["tokens"] for record in st.session_state["history_data"])
    st.metric("总 Token", f"{total_tokens:,}")

st.markdown("---")

# 决策分布
if action_counts:
    st.subheader("决策类型分布")
    for action, count in action_counts.items():
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**{action}:**")
        with col2:
            st.progress(count / len(st.session_state["history_data"]))
            st.write(f"{count} 次")

st.markdown("---")


# --- 成本分析 ---
st.header("成本分析", divider="blue")

# 按股票统计成本
stock_costs = {}
for record in st.session_state["history_data"]:
    symbol = record["symbol"]
    if symbol not in stock_costs:
        stock_costs[symbol] = {"cost": 0.0, "tokens": 0, "count": 0}
    stock_costs[symbol]["cost"] += record["cost_usd"]
    stock_costs[symbol]["tokens"] += record["tokens"]
    stock_costs[symbol]["count"] += 1

if stock_costs:
    st.subheader("按股票统计")

    # 创建表格数据
    table_data = []
    for symbol, data in stock_costs.items():
        table_data.append({
            "股票代码": symbol,
            "分析次数": data["count"],
            "总成本 (USD)": f"${data['cost']:.4f}",
            "平均成本 (USD)": f"${data['cost'] / data['count']:.4f}",
            "总 Token": f"{data['tokens']:,}",
            "平均 Token": f"{data['tokens'] // data['count']:,}",
        })

    st.dataframe(
        table_data,
        width="stretch",
    )

st.markdown("---")


# --- 导出功能 ---
st.header("导出", divider="blue")

col1, col2 = st.columns(2)
with col1:
    if st.button("📥 导出为 CSV", type="primary"):
        st.success("历史记录已导出为 CSV（实际实现会下载文件）")

with col2:
    if st.button("📄 导出为 Excel"):
        st.success("历史记录已导出为 Excel（实际实现会下载文件）")
