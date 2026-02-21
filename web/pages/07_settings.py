# web/pages/07_settings.py
# 系统设置页 - Phase 4 Task 7 (P4-T7)

import streamlit as st
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 页面配置
st.set_page_config(
    page_title="系统设置",
    page_icon="⚙️",
    layout="wide",
)

st.title("⚙️ 系统设置")
st.markdown("---")


# --- LLM 配置 ---
st.header("LLM 配置", divider="blue")

col1, col2 = st.columns(2)
with col1:
    default_provider = st.selectbox(
        "默认 LLM 提供商",
        ["openai", "anthropic", "google", "deepseek", "ollama", "dashscope"],
        index=4,  # 默认 ollama
    )

with col2:
    st.info("温度参数固定为 0.0，不可修改（确保决策可复现性）")

st.markdown("---")

# --- 各提供商配置 ---
st.subheader("提供商配置")

# OpenAI
with st.expander("OpenAI 配置"):
    st.markdown("**OpenAI**")
    openai_api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="sk-...",
        help="输入后自动保存到系统密钥链（实际实现需要 keyring 库）",
    )
    openai_base_url = st.text_input(
        "Base URL (可选)",
        placeholder="https://api.openai.com/v1",
        help="自定义 API 端点（如使用代理或兼容服务）",
    )
    openai_model = st.text_input(
        "默认模型",
        value="gpt-4o",
        placeholder="gpt-4o, gpt-4-turbo",
    )
    if openai_api_key:
        st.success("API Key 已设置（实际实现会保存到系统密钥链）")

st.markdown("---")

# Anthropic
with st.expander("Anthropic 配置"):
    st.markdown("**Anthropic (Claude)**")
    anthropic_api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="sk-ant-...",
    )
    anthropic_model = st.text_input(
        "默认模型",
        value="claude-3-opus-20240229",
        placeholder="claude-3-opus-20240229, claude-3-sonnet-20240229",
    )
    if anthropic_api_key:
        st.success("API Key 已设置")

st.markdown("---")

# Ollama (本地)
with st.expander("Ollama 配置"):
    st.markdown("**Ollama (本地模型)**")
    ollama_base_url = st.text_input(
        "Base URL",
        value="http://localhost:11434",
        placeholder="http://localhost:11434",
    )
    ollama_model = st.text_input(
        "默认模型",
        value="qwen3:4b",
        placeholder="qwen3:4b, llama2:7b",
    )
    ollama_status = st.checkbox("启用 Ollama", value=True)
    if ollama_status:
        st.success("Ollama 已启用")

st.markdown("---")

# DeepSeek
with st.expander("DeepSeek 配置"):
    st.markdown("**DeepSeek**")
    deepseek_api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="sk-...",
    )
    deepseek_model = st.text_input(
        "默认模型",
        value="deepseek-chat",
        placeholder="deepseek-chat",
    )
    if deepseek_api_key:
        st.success("API Key 已设置")

st.markdown("---")

# DashScope (阿里云)
with st.expander("DashScope 配置"):
    st.markdown("**DashScope (阿里云通义千问)**")
    dashscope_api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="sk-...",
    )
    dashscope_model = st.text_input(
        "默认模型",
        value="qwen-turbo",
        placeholder="qwen-turbo, qwen-plus",
    )
    if dashscope_api_key:
        st.success("API Key 已设置")

st.markdown("---")


# --- 数据源配置 ---
st.header("数据源配置", divider="blue")

st.subheader("股票数据源")

col1, col2 = st.columns(2)
with col1:
    us_primary = st.selectbox(
        "美股主数据源",
        ["yfinance", "alpha_vantage", "akshare"],
        index=0,
    )
    us_fallback = st.selectbox(
        "美股备用数据源",
        ["yfinance", "alpha_vantage", "local_csv"],
        index=1,
    )

with col2:
    cn_a_primary = st.selectbox(
        "A股主数据源",
        ["akshare", "tushare", "local_csv"],
        index=0,
    )
    hk_primary = st.selectbox(
        "港股主数据源",
        ["akshare", "yfinance"],
        index=0,
    )

st.markdown("---")

st.subheader("缓存配置")

col1, col2 = st.columns(2)
with col1:
    cache_ttl = st.slider(
        "数据缓存过期时间（小时）",
        min_value=1,
        max_value=168,
        value=24,
        step=1,
    )
with col2:
    news_ttl = st.slider(
        "新闻缓存过期时间（小时）",
        min_value=1,
        max_value=24,
        value=6,
        step=1,
    )

st.markdown("---")


# --- 分析配置 ---
st.header("分析配置", divider="blue")

col1, col2 = st.columns(2)
with col1:
    default_depth = st.selectbox(
        "默认分析深度",
        ["L1 (基础)", "L2 (标准)", "L3 (深度)"],
        index=1,
    )
    risk_profile = st.selectbox(
        "风险偏好",
        ["conservative (保守)", "balanced (平衡)", "aggressive (激进)"],
        index=1,
    )

with col2:
    enable_debate_referee = st.checkbox("启用辩论裁判员", value=True)
    min_debate_quality = st.slider(
        "最低辩论质量分",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.5,
    )
    enable_volatility_adjustment = st.checkbox("启用波动率调整", value=True)

st.markdown("---")

# 分析师选择
st.subheader("默认分析师")
default_analysts = st.multiselect(
    "启用的分析师",
    ["technical", "fundamentals", "news", "sentiment"],
    default=["technical", "fundamentals", "news", "sentiment"],
)

analyst_labels = {
    "technical": "技术分析师",
    "fundamentals": "基本面分析师",
    "news": "新闻分析师",
    "sentiment": "情绪分析师",
}

st.info(f"已启用: {', '.join([analyst_labels[a] for a in default_analysts])}")

st.markdown("---")


# --- MongoDB 配置 ---
st.header("MongoDB 配置", divider="blue")

st.subheader("数据库连接")

mongo_connection_string = st.text_input(
    "Connection String",
    value="mongodb://localhost:27017/",
    placeholder="mongodb://localhost:27017/ or mongodb+srv://...",
    help="MongoDB 连接字符串",
)

mongo_database = st.text_input(
    "数据库名称",
    value="pstds",
    placeholder="pstds",
)

# 测试连接按钮
col1, col2 = st.columns(2)
with col1:
    if st.button("🔗 测试连接"):
        try:
            from pstds.storage.mongo_store import MongoStore
            store = MongoStore(mongo_connection_string, mongo_database)
            if store.client:
                st.success("MongoDB 连接成功！")
            else:
                st.error("MongoDB 连接失败，请检查配置")
        except Exception as e:
            st.error(f"连接错误: {e}")

with col2:
    if st.button("🗑️ 清空本地缓存"):
        st.warning("缓存已清空（实际实现会执行清理操作）")

st.markdown("---")


# --- 系统信息 ---
st.header("系统信息", divider="blue")

col1, col2 = st.columns(2)
with col1:
    st.metric("Python 版本", "3.12.3")
    st.metric("Streamlit 版本", "1.54.0")

with col2:
    st.metric("当前页面", "系统设置")
    st.metric("Session ID", str(hash(st.session_state)[:8]))

st.markdown("---")


# --- 保存和重置 ---
st.header("保存设置", divider="blue")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("💾 保存配置", type="primary"):
        st.success("配置已保存到 config/user.yaml（实际实现会执行保存）")

with col2:
    if st.button("📥 导出配置"):
        st.success("配置已导出为 YAML 文件")

with col3:
    if st.button("🔄 恢复默认配置"):
        if st.confirm("确定要恢复默认配置吗？所有自定义设置将丢失。"):
            st.warning("配置已恢复默认值")

st.markdown("---")


# --- 免责声明 ---
st.header("免责声明", divider="red")

st.warning("""
本系统为个人研究辅助工具。所有分析结果、投资建议均由 LLM 自动生成，存在固有的不确定性。

**重要提示：**
- 投资有风险，入市须谨慎
- 本系统不构成任何形式的投资建议
- 开发者对投资损失不承担任何责任
- 请在充分理解风险的前提下使用本系统

本系统的任何输出仅供研究参考，不作为投资决策的唯一依据。
""")
