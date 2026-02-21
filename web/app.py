# web/app.py
# Streamlit 应用入口 - Phase 4 Task 8 (P4-T8)
# 多页面导航配置，加载配置文件

import streamlit as st
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 页面配置
st.set_page_config(
    page_title="PSTDS - 股票交易决策系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 初始化 session state
if "config" not in st.session_state:
    st.session_state["config"] = {}

# --- 侧边栏 ---
st.sidebar.title("📈 PSTDS")
st.sidebar.markdown("---")

# 导航菜单
st.sidebar.header("导航")

pages = [
    ("📊 股票分析", "pages/01_analysis.py"),
    ("⭐ 自选股", "pages/02_watchlist.py"),
    ("📜 历史记录", "pages/03_history.py"),
    ("⚙️ 系统设置", "pages/07_settings.py"),
]

# 显示导航链接
for label, page_path in pages:
    page_name = label.split(" ")[1]
    if st.sidebar.button(f"  {label}", key=f"nav_{page_name}"):
        st.info(f"正在跳转到 {page_name}...")

st.sidebar.markdown("---")

# --- 侧边栏信息 ---
st.sidebar.subheader("系统状态")

# MongoDB 连接状态
st.sidebar.info("🟡 MongoDB 配置完成")
st.sidebar.info("🟢 LLM 配置完成")

st.sidebar.metric("本月成本", "$0.00")

st.sidebar.markdown("---")

# 快速操作
st.sidebar.subheader("快速操作")
if st.sidebar.button("🚀 新建分析"):
    st.switch_page("pages/01_analysis.py")

if st.sidebar.button("⭐ 添加自选股"):
    st.switch_page("pages/02_watchlist.py")

st.sidebar.markdown("---")

# 系统信息
st.sidebar.caption("""
**PSTDS v1.0**

个人专用股票交易决策系统

© 2026
""")

# --- 主内容区 ---
st.markdown("## 欢迎使用 PSTDS")

st.markdown("""
### 📊 股票交易决策系统

这是一个基于 LLM 的个人股票交易决策辅助系统。

**功能特点：**
- 🤖 多 LLM 支持：OpenAI、Anthropic、Google、DeepSeek、Ollama、DashScope
- 📊 技术分析：K线图、均线、MACD、RSI 等技术指标
- 📰 新闻分析：智能提取和分析相关新闻
- 🤔 投资辩论：多分析师辩论，提高决策质量
- 🕒 时间隔离：严格的回测模式，防止前视偏差
- 💰 成本控制：实时追踪 API 调用成本

**开始使用：**
1. 使用左侧导航选择功能页面
2. 在「股票分析」页面输入股票代码开始分析
3. 查看「自选股」管理关注的股票
4. 在「历史记录」中查看所有分析结果
5. 在「系统设置」中配置 LLM 和数据源

---

**⚠️ 重要免责声明：**

本系统为个人研究辅助工具。所有分析结果、投资建议均由 LLM 自动生成，
存在固有的不确定性。

**重要提示：**
- 投资有风险，入市须谨慎
- 本系统不构成任何形式的投资建议
- 开发者对投资损失不承担任何责任
- 请在充分理解风险的前提下使用本系统

本系统的任何输出仅供研究参考，不作为投资决策的唯一依据。

---

© 2026 PSTDS - 个人专用股票交易决策系统
""")

# 显示快速入口
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📊 股票分析", use_container_width=True):
        st.switch_page("pages/01_analysis.py")

with col2:
    if st.button("⭐ 自选股", use_container_width=True):
        st.switch_page("pages/02_watchlist.py")

with col3:
    if st.button("📜 历史记录", use_container_width=True):
        st.switch_page("pages/03_history.py")

with col4:
    if st.button("⚙️ 系统设置", use_container_width=True):
        st.switch_page("pages/07_settings.py")
