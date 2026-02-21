# web/pages/01_analysis.py
# Streamlit 主分析页 - Phase 4 Task 4 (P4-T4)
# DDD v2.0 第 5.1 节：8 步交互流程

import streamlit as st
from datetime import date, datetime
from typing import Dict, Any
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pstds.temporal.context import TemporalContext
from pstds.agents.output_schemas import TradeDecision, DataSource


# 页面配置
st.set_page_config(
    page_title="股票分析",
    page_icon="📊",
    layout="wide",
)

st.title("📊 股票交易决策分析")
st.markdown("---")


# --- 步骤 1: 股票选择 ---
st.header("步骤 1: 选择股票", divider="blue")

symbol = st.text_input(
    "股票代码",
    placeholder="例如: AAPL, 600519, 0700.HK",
    value="AAPL",
    max_chars=20,
)

market_type = st.selectbox(
    "市场类型",
    ["US", "CN_A", "HK"],
    index=0,
)

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


# --- 步骤 2: 分析日期选择 ---
st.header("步骤 2: 选择分析日期", divider="blue")

analysis_mode = st.radio(
    "分析模式",
    ["LIVE (实时)", "BACKTEST (回测)"],
    horizontal=True,
)

if analysis_mode == "LIVE (实时)":
    analysis_date = date.today()
    st.info(f"实时模式: 使用今日 {analysis_date} 进行分析")
else:
    analysis_date = st.date_input(
        "回测日期",
        value=date(2024, 1, 2),
        min_value=date(2020, 1, 1),
        max_value=date.today(),
    )
    st.info(f"回测模式: 模拟 {analysis_date} 当天的分析")

st.markdown("---")


# --- 步骤 3: LLM 配置 ---
st.header("步骤 3: LLM 配置", divider="blue")

col1, col2 = st.columns(2)
with col1:
    llm_provider = st.selectbox(
        "LLM 提供商",
        ["openai", "anthropic", "google", "deepseek", "ollama", "dashscope"],
        index=5,  # 默认 ollama
    )
with col2:
    analysis_depth = st.selectbox(
        "分析深度",
        ["L1 (基础)", "L2 (标准)", "L3 (深度)"],
        index=1,
    )

model_name = st.text_input(
    "模型名称",
    placeholder="例如: gpt-4o, claude-3-opus-20240229, qwen3:4b",
    value="qwen3:4b",
)

st.markdown("---")


# --- 步骤 4: 分析师选择 ---
st.header("步骤 4: 选择分析师", divider="blue")

available_analysts = ["technical", "fundamentals", "news", "sentiment"]
selected_analysts = st.multiselect(
    "启用的分析师",
    available_analysts,
    default=available_analysts,
)

analyst_labels = {
    "technical": "技术分析师",
    "fundamentals": "基本面分析师",
    "news": "新闻分析师",
    "sentiment": "情绪分析师",
}

if selected_analysts:
    st.success(f"已启用: {', '.join([analyst_labels[a] for a in selected_analysts])}")
else:
    st.warning("请至少选择一个分析师")

st.markdown("---")


# --- 步骤 5: 高级选项 ---
st.header("步骤 5: 高级选项", divider="blue")

with st.expander("展开高级选项"):
    enable_debate_referee = st.checkbox(
        "启用辩论裁判员",
        value=True,
        help="评估分析师之间的辩论质量"
    )

    min_debate_quality_score = st.slider(
        "最低辩论质量分",
        min_value=0.0,
        max_value=10.0,
        value=5.0,
        step=0.5,
        help="低于此分数的辩论将被标记为低质量"
    )

    enable_volatility_adjustment = st.checkbox(
        "启用波动率调整",
        value=True,
        help="根据历史波动率调整决策阈值"
    )

    risk_profile = st.selectbox(
        "风险偏好",
        ["conservative (保守)", "balanced (平衡)", "aggressive (激进)"],
        index=1,
    )

st.markdown("---")


# --- 步骤 6: 成本估算 ---
st.header("步骤 6: 成本估算", divider="blue")

with st.expander("展开成本估算"):
    # 估算 token 使用量
    estimated_tokens = {
        "L1": 20000,
        "L2": 60000,
        "L3": 120000,
    }

    depth_token = estimated_tokens.get(analysis_depth.split()[0], 60000)

    # 根据 LLM 提供商和模型估算成本
    price_per_million = {
        "openai": 5.0,
        "anthropic": 15.0,
        "google": 3.5,
        "deepseek": 0.14,
        "ollama": 0.0,  # 本地免费
        "dashscope": 0.5,
    }

    price = price_per_million.get(llm_provider, 1.0)
    estimated_cost = (depth_token / 1_000_000) * price

    col1, col2 = st.columns(2)
    with col1:
        st.metric("预计 Token 使用", f"{depth_token:,}")
    with col2:
        st.metric("预计成本 (USD)", f"${estimated_cost:.4f}")

st.markdown("---")


# --- 步骤 7: 执行分析 ---
st.header("步骤 7: 执行分析", divider="blue")

if not selected_analysts:
    st.warning("请先选择至少一个分析师")
else:
    if st.button("🚀 开始分析", type="primary", use_container_width=True):
        # 创建 TemporalContext
        if analysis_mode == "LIVE (实时)":
            ctx = TemporalContext.for_live(analysis_date)
        else:
            ctx = TemporalContext.for_backtest(analysis_date)

        st.session_state["analysis_running"] = True
        st.session_state["ctx"] = ctx
        st.session_state["symbol"] = symbol
        st.session_state["market_type"] = market_type
        st.session_state["config"] = {
            "llm_provider": llm_provider,
            "model_name": model_name,
            "analysis_depth": analysis_depth,
            "selected_analysts": selected_analysts,
            "enable_debate_referee": enable_debate_referee,
            "min_debate_quality_score": min_debate_quality_score,
            "enable_volatility_adjustment": enable_volatility_adjustment,
            "risk_profile": risk_profile,
        }

        # 创建进度条
        progress_bar = st.progress(0, text="初始化...")
        status_text = st.empty()

        # 模拟分析流程（实际实现会调用 ExtendedTradingAgentsGraph）
        steps = [
            ("技术分析", 0.15, "正在进行技术分析..."),
            ("基本面分析", 0.30, "正在获取基本面数据..."),
            ("新闻分析", 0.40, "正在分析相关新闻..."),
            ("情绪分析", 0.50, "正在分析市场情绪..."),
            ("投资辩论", 0.80, "正在进行多轮投资辩论..."),
            ("风险评估", 0.90, "正在进行风险评估..."),
            ("决策生成", 1.00, "正在生成最终决策..."),
        ]

        for step_name, progress, status in steps:
            progress_bar.progress(progress)
            status_text.text(status)
            # 实际实现中会调用对应的分析节点
            import time
            time.sleep(0.5)

        progress_bar.progress(1.0, text="分析完成！")
        status_text.empty()

        # 创建模拟的 TradeDecision
        mock_decision = TradeDecision(
            action="BUY",
            confidence=0.72,
            conviction="MEDIUM",
            primary_reason="技术突破，基本面强劲",
            insufficient_data=False,
            target_price_low=1680.0,
            target_price_high=1750.0,
            time_horizon="2-4 weeks",
            risk_factors=["市场波动", "行业竞争"],
            data_sources=[DataSource(
                name="yfinance",
                url=None,
                data_timestamp=datetime.utcnow(),
                market_type=market_type,
                fetched_at=datetime.utcnow(),
            )],
            analysis_date=analysis_date,
            analysis_timestamp=datetime.utcnow(),
            volatility_adjustment=1.0,
            debate_quality_score=7.5,
            symbol=symbol,
            market_type=market_type,
        )

        st.session_state["decision"] = mock_decision
        st.session_state["analysis_running"] = False

        st.success("分析完成！")

        # 显示结果
        st.session_state.show_result = True

st.markdown("---")


# --- 步骤 8: 结果展示 ---
if st.session_state.get("show_result", False):
    st.header("步骤 8: 分析结果", divider="green")

    decision = st.session_state.get("decision")

    if decision:
        # 决策摘要
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("决策", decision.action)
        with col2:
            st.metric("置信度", f"{decision.confidence * 100:.1f}%")
        with col3:
            st.metric("信心度", decision.conviction)

        st.markdown("---")

        # 主要理由
        st.subheader("主要决策理由")
        st.write(decision.primary_reason)

        st.markdown("---")

        # 价格目标
        if decision.target_price_low and decision.target_price_high:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("目标价下限", f"${decision.target_price_low:.2f}")
            with col2:
                st.metric("目标价上限", f"${decision.target_price_high:.2f}")
            st.write(f"时间框架: {decision.time_horizon}")

        st.markdown("---")

        # 风险因素
        st.subheader("风险因素")
        for risk in decision.risk_factors:
            st.warning(f"⚠️ {risk}")

        st.markdown("---")

        # 数据来源
        st.subheader("数据来源")
        for source in decision.data_sources:
            st.info(f"📊 {source.name}")

        # 辩论质量
        st.metric("辩论质量分", f"{decision.debate_quality_score:.1f}/10.0")

        st.markdown("---")

        # 保存按钮
        if st.button("💾 保存分析结果"):
            st.success("分析结果已保存（实际实现会保存到 MongoDB）")
else:
    st.info("请完成以上步骤并点击「开始分析」按钮")
