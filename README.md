# PSTDS - 个人专用股票交易决策系统 v1.0

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/anthropics/claude-code/actions/workflows/status)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://choosealicense.com/licenses/mit)

> 基于 LLM 的个人股票交易决策系统，支持多源数据、时间隔离、回测验证。

## 重要声明

本系统为个人研究辅助工具。所有分析结果、投资建议均由 LLM 自动生成，存在固有的不确定性。

**重要提示：**
- 投资有风险，入市须谨慎
- 本系统不构成任何形式的投资建议
- 开发者对投资损失不承担任何责任
- 请在充分理解风险的前提下使用本系统

本系统的任何输出仅供研究参考，不作为投资决策的唯一依据。

---

## 快速开始

### 环境要求

- Python 3.10+
- MongoDB 7.0+
- Redis 7.0+
- 4GB+ RAM

### 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/pstds.git
cd pstds

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选）
cp config/default.yaml config/user.yaml
# 编辑 user.yaml 添加您的 API Keys
```

### Docker 部署（推荐）

```bash
# 使用 Docker Compose 一键启动所有服务
docker-compose up -d

# 访问 Web UI
open http://localhost:8501
```

### 本地启动

```bash
# 启动 Streamlit 应用
cd web
streamlit run app.py

# 或使用启动脚本
python start.py
```

---

*© 2026 PSTDS - 个人专用股票交易决策系统*
