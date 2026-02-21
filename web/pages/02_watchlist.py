# web/pages/02_watchlist.py
# 自选股页面 - Phase 4 Task 6 (P4-T6)

import streamlit as st
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 页面配置
st.set_page_config(
    page_title="自选股",
    page_icon="⭐",
    layout="wide",
)

st.title("⭐ 自选股管理")
st.markdown("---")


# 初始化 session state
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "market_type": "US",
            "group_tags": ["科技"],
            "auto_analysis_enabled": True,
            "last_analyzed_at": None,
        },
        {
            "symbol": "600519",
            "name": "贵州茅台",
            "market_type": "CN_A",
            "group_tags": ["消费"],
            "auto_analysis_enabled": True,
            "last_analyzed_at": None,
        },
        {
            "symbol": "0700.HK",
            "name": "腾讯控股",
            "market_type": "HK",
            "group_tags": ["科技"],
            "auto_analysis_enabled": False,
            "last_analyzed_at": None,
        },
    ]


# --- 添加股票 ---
st.header("添加新股票", divider="blue")

with st.form("add_stock_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        symbol_input = st.text_input("股票代码", placeholder="AAPL, 600519, 0700.HK")
    with col2:
        name_input = st.text_input("公司名称", placeholder="Apple Inc.")
    with col3:
        market_type_input = st.selectbox("市场类型", ["US", "CN_A", "HK"])

    group_tags_input = st.multiselect(
        "标签分组",
        ["科技", "消费", "金融", "医药", "能源", "其他"],
        default=[],
    )

    auto_analysis_input = st.checkbox("启用自动分析")

    submitted = st.form_submit_button("➕ 添加", type="primary")

    if submitted and symbol_input and name_input:
        # 根据股票代码推断市场类型
        if symbol_input.endswith(".HK"):
            inferred_market = "HK"
        elif symbol_input.isdigit():
            inferred_market = "CN_A"
        else:
            inferred_market = "US"

        new_stock = {
            "symbol": symbol_input.upper(),
            "name": name_input,
            "market_type": market_type_input,
            "group_tags": group_tags_input,
            "auto_analysis_enabled": auto_analysis_input,
            "last_analyzed_at": None,
        }

        st.session_state["watchlist"].append(new_stock)
        st.success(f"已添加: {symbol_input} - {name_input}")
        st.rerun()

st.markdown("---")


# --- 标签筛选 ---
st.header("筛选", divider="blue")

all_tags = []
for stock in st.session_state["watchlist"]:
    all_tags.extend(stock.get("group_tags", []))

all_tags = sorted(list(set(all_tags)))
selected_tags = st.multiselect("按标签筛选", all_tags, default=all_tags)

st.markdown("---")


# --- 自选股列表 ---
st.header("自选股列表", divider="blue")

filtered_watchlist = [
    stock for stock in st.session_state["watchlist"]
    if any(tag in selected_tags for tag in stock.get("group_tags", []))
]

if filtered_watchlist:
    for stock in filtered_watchlist:
        with st.expander(
            f"{stock['symbol']} - {stock['name']} "
            f"({'🔔' if stock.get('auto_analysis_enabled') else '🔕'})",
            expanded=False,
        ):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**市场:** {stock['market_type']}")
                if stock.get("last_analyzed_at"):
                    st.write(f"**最后分析:** {stock['last_analyzed_at']}")

            with col2:
                tags = stock.get("group_tags", [])
                if tags:
                    st.write("**标签:**")
                    for tag in tags:
                        st.badge(tag)

            with col3:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"📊 分析", key=f"analyze_{stock['symbol']}"):
                        # 保存选中的股票信息到 session state
                        st.session_state.selected_stock = {
                            "symbol": stock['symbol'],
                            "market_type": stock['market_type'],
                            "name": stock['name']
                        }
                        st.switch_page("pages/01_analysis.py")

                with col_btn2:
                    if st.button(f"🗑️ 删除", key=f"delete_{stock['symbol']}"):
                        st.session_state["watchlist"] = [
                            s for s in st.session_state["watchlist"]
                            if s["symbol"] != stock["symbol"]
                        ]
                        st.warning(f"已删除: {stock['symbol']}")
                        st.rerun()
else:
    st.info("没有符合条件的自选股")

st.markdown("---")


# --- 批量操作 ---
st.header("批量操作", divider="blue")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔄 分析所有自选股", type="primary"):
        st.success("已启动批量分析（实际实现会异步执行）")

with col2:
    if st.button("📥 导出自选股"):
        st.success("自选股已导出（实际实现会下载 CSV 文件）")

with col3:
    if st.button("⚙️ 批量设置"):
        with st.expander("批量设置"):
            enable_all = st.checkbox("为所有股票启用自动分析")
            if st.button("应用设置"):
                for stock in st.session_state["watchlist"]:
                    stock["auto_analysis_enabled"] = enable_all
                st.success("批量设置已应用")
                st.rerun()

st.markdown("---")


# --- 统计信息 ---
st.header("统计信息", divider="blue")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("总数量", len(st.session_state["watchlist"]))
with col2:
    auto_enabled_count = sum(
        1 for stock in st.session_state["watchlist"]
        if stock.get("auto_analysis_enabled", False)
    )
    st.metric("自动分析", auto_enabled_count)
with col3:
    analyzed_count = sum(
        1 for stock in st.session_state["watchlist"]
        if stock.get("last_analyzed_at") is not None
    )
    st.metric("已分析", analyzed_count)
