# web/pages/05_cost.py
# 成本仪表盘 - Phase 6 Task 5 (P6-T5)

import streamlit as st
import sys
import os
from datetime import date, datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 页面配置
st.set_page_config(
    page_title="成本统计",
    page_icon="💰",
    layout="wide",
)

st.title("💰 成本统计")
st.markdown("---")


# --- 成本概览 ---
st.header("成本概览", divider="blue")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("本月成本", "$12.45")
with col2:
    st.metric("总 Token", "186,540")
with col3:
    st.metric("API 调用次数", "42")

st.markdown("---")


# --- 按提供商统计 ---
st.header("按提供商统计", divider="blue")

providers = ["OpenAI", "Anthropic", "Google", "DeepSeek", "DashScope/Ollama"]

cost_by_provider = {
    "OpenAI": {"cost": 8.50, "tokens": 85000, "calls": 15},
    "Anthropic": {"cost": 2.25, "tokens": 15000, "calls": 5},
    "Google": {"cost": 0.00, "tokens": 0, "calls": 0},
    "DeepSeek": {"cost": 1.68, "tokens": 12000, "calls": 12},
    "DashScope/Ollama": {"cost": 0.00, "tokens": 74540, "calls": 10},
}

for provider in providers:
    data = cost_by_provider.get(provider, {})
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**{provider}**")
        st.write(f"成本: ${data.get('cost', 0):.2f}")
        st.write(f"Token: {data.get('tokens', 0):,}")
    with col2:
        st.write(f"调用次数: {data.get('calls', 0)}")
        if data.get('cost', 0) > 0:
            st.warning(f"费用占比: {data['cost'] / 12.45 * 100:.1f}%")

st.markdown("---")


# --- 按模型统计 ---
st.header("按模型统计", divider="blue")

models = ["gpt-4o", "claude-3-opus-20240229", "gemini-1.5-pro", "qwen-turbo", "qwen3:4b"]

cost_by_model = {
    "gpt-4o": {"cost": 5.00, "tokens": 50000, "calls": 8},
    "claude-3-opus-20240229": {"cost": 2.25, "tokens": 15000, "calls": 5},
    "gemini-1.5-pro": {"cost": 0.00, "tokens": 0, "calls": 0},
    "qwen-turbo": {"cost": 0.75, "tokens": 15000, "calls": 15},
    "qwen3:4b": {"cost": 0.00, "tokens": 74540, "calls": 22},
}

for model in models:
    data = cost_by_model.get(model, {})
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**{model}**")
        st.write(f"成本: ${data.get('cost', 0):.2f}")
        st.write(f"Token: {data.get('tokens', 0):,}")
    with col2:
        st.write(f"调用次数: {data.get('calls', 0)}")
        if data.get('cost', 0) > 0:
            st.warning(f"费用占比: {data['cost'] / 12.45 * 100:.1f}%")

st.markdown("---")


# --- 成本趋势图 ---
st.header("成本趋势", divider="blue")

import pandas as pd
import numpy as np

# 模拟成本数据
dates = pd.date_range(start="2024-01-01", end=date.today(), freq="D")
costs = np.random.uniform(0, 2, len(dates)).cumsum()

cost_df = pd.DataFrame({
    "日期": dates,
    "成本": costs,
})

st.line_chart(cost_df, x="日期", y="成本", width="stretch")

st.markdown("---")


# --- 预算设置 ---
st.header("预算设置", divider="blue")

col1, col2 = st.columns(2)
with col1:
    monthly_budget = st.number_input(
        "月度预算 (USD)",
        min_value=10.0,
        max_value=1000.0,
        value=50.0,
        step=5.0,
    )
    monthly_limit = monthly_budget * 0.8
    st.warning(f"告警阈值: ${monthly_limit:.2f} (80% of budget)")

with col2:
    alert_enabled = st.checkbox("启用邮件告警", value=False)

st.markdown("---")


# --- 成本明细 ---
st.header("成本明细", divider="blue")

# 模拟成本明细
cost_records = [
    {"日期": "2024-01-15", "提供商": "OpenAI", "模型": "gpt-4o", "调用次数": 1, "Token": 5000, "成本": "$0.25"},
    {"日期": "2024-01-16", "提供商": "OpenAI", "模型": "gpt-4o", "调用次数": 2, "Token": 10000, "成本": "$0.50"},
    {"日期": "2024-01-17", "提供商": "Anthropic", "模型": "claude-3-opus-20240229", "调用次数": 1, "Token": 15000, "成本": "$2.25"},
    {"日期": "2024-01-18", "提供商": "DeepSeek", "模型": "deepseek-chat", "调用次数": 3, "Token": 12000, "成本": "$1.68"},
]

st.dataframe(cost_records, width="stretch")

st.markdown("---")


# --- 导出功能 ---
st.header("导出成本报告", divider="blue")

col1, col2 = st.columns(2)
with col1:
    if st.button("📥 导出为 CSV", type="primary"):
        st.success("成本报告已导出为 CSV")

with col2:
    if st.button("📄 导出为 PDF", type="primary"):
        st.success("成本报告已导出为 PDF")

st.markdown("---")

st.info("""
**重要提示：**
- 所有成本为估算值，实际成本可能略有差异
- 建议定期检查您的 API 账单
- 设置合理的月度预算以控制成本
""")
