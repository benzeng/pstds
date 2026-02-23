# web/pages/02_watchlist.py
# 自选股页面 - Phase 4 Task 6 (P4-T6)

import streamlit as st
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pstds.storage.watchlist_store import WatchlistStore

# 页面配置
st.set_page_config(
    page_title="自选股",
    page_icon="⭐",
    layout="wide",
)

st.title("⭐ 自选股管理")
st.markdown("---")


# 初始化 WatchlistStore
if "watchlist_store" not in st.session_state:
    st.session_state["watchlist_store"] = WatchlistStore()
    store = st.session_state["watchlist_store"]

    # 首次运行，添加默认股票（如果数据库为空）
    if store.get_count() == 0:
        defaults = [
            {"symbol": "AAPL", "name": "Apple Inc.", "market_type": "US", "group_tags": ["科技"]},
            {"symbol": "600519", "name": "贵州茅台", "market_type": "CN_A", "group_tags": ["消费"]},
            {"symbol": "0700.HK", "name": "腾讯控股", "market_type": "HK", "group_tags": ["科技"]},
        ]
        for stock in defaults:
            store.add_stock(**stock)

# 获取存储实例
store = st.session_state["watchlist_store"]


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

        # 使用市场类型输入（如果用户手动选择了）
        final_market_type = market_type_input

        # 添加到持久化存储
        success = store.add_stock(
            symbol=symbol_input.upper(),
            name=name_input,
            market_type=final_market_type,
            group_tags=group_tags_input,
            auto_analysis_enabled=auto_analysis_input,
        )

        if success:
            st.success(f"已添加: {symbol_input.upper()} - {name_input}")
            st.rerun()
        else:
            st.error(f"添加失败：{symbol_input.upper()} 可能已存在")
            st.info("💡 提示：如果股票已存在，请使用「批量设置」或「编辑」功能更新信息")

st.markdown("---")


# --- 标签筛选 ---
st.header("筛选", divider="blue")

# 获取所有股票
all_stocks = store.get_all()

# 收集所有标签
all_tags = []
for stock in all_stocks:
    all_tags.extend(stock.get("group_tags", []))

all_tags = sorted(list(set(all_tags)))
selected_tags = st.multiselect("按标签筛选", all_tags, default=[])

# 显示筛选状态
if selected_tags:
    filtered = store.get_by_tags(selected_tags, require_match=True)
    st.info(f"🔍 已筛选 {len(filtered)} 个股票（标签：{', '.join(selected_tags)}）")
else:
    st.info(f"📋 显示全部 {len(all_stocks)} 个股票")

st.markdown("---")


# --- 自选股列表 ---
st.header("自选股列表", divider="blue")

# 根据标签筛选
if selected_tags:
    # 只显示有匹配标签的股票
    filtered_watchlist = store.get_by_tags(selected_tags, require_match=True)
else:
    # 显示所有股票（包括没有标签的股票）
    filtered_watchlist = all_stocks

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
                        if store.delete_stock(stock['symbol']):
                            st.warning(f"✅ 已删除: {stock['symbol']}")
                            st.rerun()
                        else:
                            st.error(f"❌ 删除失败: {stock['symbol']}")
else:
    st.info("没有符合条件的自选股")

st.markdown("---")


# --- 批量操作 ---
st.header("批量操作", divider="blue")

col1, col2, col3, col4 = st.columns(4)
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
                all_stocks = store.get_all()
                for stock in all_stocks:
                    store.update_stock(stock['symbol'], auto_analysis_enabled=enable_all)
                st.success("批量设置已应用")
                st.rerun()

with col4:
    if st.button("🗑️ 清空所有", type="secondary"):
        if st.session_state.get("confirm_clear", False):
            count = store.get_count()
            cleared = store.clear_all()
            if cleared > 0:
                st.success(f"✅ 已清空 {cleared} 个股票")
                st.session_state.confirm_clear = False
                st.rerun()
            else:
                st.info("数据库已为空")
        else:
            st.session_state.confirm_clear = True
            st.warning("⚠️ 确认要清空所有自选股？请再次点击按钮确认")

st.markdown("---")


# --- 统计信息 ---
st.header("统计信息", divider="blue")

# 获取统计数据
all_stocks = store.get_all()
auto_enabled_count = sum(
    1 for stock in all_stocks
    if stock.get("auto_analysis_enabled", False)
)
analyzed_count = sum(
    1 for stock in all_stocks
    if stock.get("last_analyzed_at") is not None
)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("总数量", len(all_stocks))
with col2:
    st.metric("自动分析", auto_enabled_count)
with col3:
    st.metric("已分析", analyzed_count)
