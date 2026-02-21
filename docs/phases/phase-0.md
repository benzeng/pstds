# Phase 0：环境搭建与验证

**目标**：Docker 服务就绪，TradingAgents 原版可运行，项目骨架创建完成。

**前置条件**（由用户在运行 Claude Code 前手动完成）：
```bash
git clone https://github.com/TauricResearch/TradingAgents.git pstds
cd pstds
python -m venv .venv && source .venv/bin/activate
```

---

## 任务列表

**P0-T1：创建 docs/ 目录并转换设计文档**
```bash
mkdir -p docs
# 将用户提供的 .docx 文件转换为 .md（便于 Claude Code 读取）
for f in PSTDS_1_功能需求文档_FRD_v2.docx PSTDS_2_系统架构文档_SAD_v2.docx \
          PSTDS_3_详细设计文档_DDD_v2.docx PSTDS_4_接口契约规范_ISD_v1.docx \
          PSTDS_5_测试规范文档_TSD_v1.docx; do
    [ -f "$f" ] && pandoc "$f" -o "docs/${f%.docx}.md" && echo "✓ $f"
done
```

**P0-T2：创建项目骨架目录**
```bash
mkdir -p pstds/{temporal,agents,llm,backtest,memory,scheduler,storage,export,notify}
mkdir -p pstds/data/adapters
mkdir -p web/{pages,components}
mkdir -p tests/{unit,adapters,integration}
mkdir -p tests/fixtures/{ohlcv,fundamentals,news,llm_responses}
mkdir -p data/{raw/{prices,news,fundamentals},cache,backtest,reports,logs}
mkdir -p config
# 创建所有 __init__.py
find pstds tests -type d -exec touch {}/__init__.py \;
```

**P0-T3：创建 requirements.txt**
```
# 核心框架
tradingagents>=0.2.0
langchain>=0.2.0
langgraph>=0.1.0

# 数据
yfinance>=0.2.40
akshare>=1.14.0
pandas>=2.0.0
pandas-ta>=0.3.14b0
pyarrow>=15.0.0
requests>=2.31.0

# LLM
openai>=1.30.0
anthropic>=0.28.0
google-generativeai>=0.5.0

# 数据验证
pydantic>=2.7.0

# 存储
pymongo>=4.7.0

# 向量记忆
chromadb>=0.5.0

# Web UI
streamlit>=1.35.0
plotly>=5.22.0

# 调度
apscheduler>=3.10.0

# 导出
python-docx>=1.1.0
weasyprint>=62.0
markdown>=3.6

# 通知
plyer>=2.1.0

# 测试
pytest>=8.2.0
pytest-cov>=5.0.0
pytest-mock>=3.14.0
pytest-asyncio>=0.23.0

# 工具
python-dotenv>=1.0.0
pyyaml>=6.0.1
cryptography>=42.0.0
```

**P0-T4：创建 config/default.yaml**
```yaml
# PSTDS v2.0 默认配置
temporal:
  enforce_isolation: true
  audit_log_path: "./data/logs/temporal_audit.jsonl"
  news_timestamp_strict: true

llm:
  provider: "ollama"
  deep_think_model: "qwen3:4b"
  quick_think_model: "qwen3:4b"
  temperature: 0.0            # 仅文档记录，实际调用硬编码为 0.0
  max_debate_rounds: 2
  ollama_base_url: "http://localhost:11434"
  token_budget:
    L0: 5000
    L1: 20000
    L2: 60000
    L3: 120000
  monthly_cost_alert_usd: 10.0
  auto_fallback_to_local: true

analysis:
  default_depth: "L2"
  risk_profile: "balanced"
  enable_volatility_adjustment: true
  analysts: ["technical", "fundamentals", "news", "sentiment"]
  debate_referee_enabled: true
  min_debate_quality_score: 5.0
  consecutive_buy_alert: 3

data:
  us_stock_primary: "yfinance"
  us_stock_fallback: "alpha_vantage"
  cn_a_stock_primary: "akshare"
  hk_stock_primary: "akshare"
  hk_stock_fallback: "yfinance"
  cache_ttl_hours: 24
  news_ttl_hours: 6
  news_relevance_threshold: 0.6
  max_news_tokens_per_item: 500
  max_fundamentals_tokens: 2000

storage:
  mongodb_uri: "mongodb://localhost:27017"
  mongodb_db: "pstds"
  sqlite_path: "./data/cache.db"
  parquet_dir: "./data/raw"
  reports_dir: "./data/reports"
  chromadb_path: "./data/vector_memory"

concurrency:
  max_parallel_stocks: 3
  rate_limit_rps: 5

notify:
  desktop_enabled: true
  email_enabled: false
  smtp_host: ""
  smtp_port: 587
  smtp_user: ""
  smtp_to: ""
```

**P0-T5：创建 docker-compose.yml**
```yaml
version: "3.9"
services:
  mongodb:
    image: mongo:7.0
    ports: ["27017:27017"]
    volumes: ["mongo_data:/data/db"]
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: ["ollama_data:/root/.ollama"]
    profiles: ["local-llm"]   # 仅在 --profile local-llm 时启动

volumes:
  mongo_data:
  ollama_data:
```

**P0-T6：创建 tests/conftest.py**
```python
# tests/conftest.py
import pytest
import json
from datetime import date
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

@pytest.fixture
def live_ctx_2024_01_02():
    """AAPL 前视偏差回归测试标准上下文"""
    from pstds.temporal.context import TemporalContext
    return TemporalContext.for_live(date(2024, 1, 2))

@pytest.fixture
def backtest_ctx_2024_01_02():
    from pstds.temporal.context import TemporalContext
    return TemporalContext.for_backtest(date(2024, 1, 2))

@pytest.fixture
def live_ctx_today():
    from pstds.temporal.context import TemporalContext
    from datetime import date
    return TemporalContext.for_live(date.today())

@pytest.fixture
def mixed_news_fixture():
    """含未来新闻的测试数据：5条合规 + 3条未来"""
    return json.loads((FIXTURES / "news/mixed_dates.json").read_text())

@pytest.fixture
def valid_decision_json():
    return json.loads((FIXTURES / "llm_responses/valid_trade_decision.json").read_text())
```

**P0-T7：创建 Fixture 数据文件**

创建 `tests/fixtures/news/mixed_dates.json`：
```json
[
  {"title": "AAPL reports strong Q4", "content": "Apple reported...", "published_at": "2024-01-01T10:00:00Z", "source": "Reuters", "url": "https://reuters.com/1", "relevance_score": 0.85, "market_type": "US", "symbol": "AAPL"},
  {"title": "Fed signals rate pause", "content": "Federal Reserve...", "published_at": "2024-01-01T14:00:00Z", "source": "Bloomberg", "url": "https://bloomberg.com/1", "relevance_score": 0.72, "market_type": "US", "symbol": "AAPL"},
  {"title": "Tech sector rally", "content": "Technology stocks...", "published_at": "2024-01-02T08:00:00Z", "source": "CNBC", "url": "https://cnbc.com/1", "relevance_score": 0.68, "market_type": "US", "symbol": "AAPL"},
  {"title": "AAPL new product launch", "content": "Apple announced...", "published_at": "2024-01-02T09:30:00Z", "source": "TechCrunch", "url": "https://techcrunch.com/1", "relevance_score": 0.91, "market_type": "US", "symbol": "AAPL"},
  {"title": "Market opens higher", "content": "Stocks opened...", "published_at": "2024-01-02T09:31:00Z", "source": "WSJ", "url": "https://wsj.com/1", "relevance_score": 0.65, "market_type": "US", "symbol": "AAPL"},
  {"title": "FUTURE: AAPL earnings beat", "content": "Apple exceeded...", "published_at": "2024-01-03T10:00:00Z", "source": "Reuters", "url": "https://reuters.com/2", "relevance_score": 0.88, "market_type": "US", "symbol": "AAPL"},
  {"title": "FUTURE: Fed cuts rates", "content": "Federal Reserve cut...", "published_at": "2024-01-04T15:00:00Z", "source": "Bloomberg", "url": "https://bloomberg.com/2", "relevance_score": 0.79, "market_type": "US", "symbol": "AAPL"},
  {"title": "FUTURE: AAPL all-time high", "content": "Apple stock hit...", "published_at": "2024-01-05T16:00:00Z", "source": "CNBC", "url": "https://cnbc.com/2", "relevance_score": 0.95, "market_type": "US", "symbol": "AAPL"}
]
```

创建 `tests/fixtures/llm_responses/valid_trade_decision.json`：
```json
{
  "action": "BUY",
  "confidence": 0.72,
  "conviction": "MEDIUM",
  "primary_reason": "强劲的技术面突破结合积极的基本面数据支撑买入决策",
  "target_price_low": 182.0,
  "target_price_high": 195.0,
  "time_horizon": "2-4 weeks",
  "risk_factors": ["宏观经济不确定性", "估值偏高风险", "竞争加剧"],
  "data_sources": [
    {"name": "yfinance", "url": null, "data_timestamp": "2024-01-02T00:00:00Z", "market_type": "US", "fetched_at": "2024-01-02T09:00:00Z"}
  ],
  "analysis_date": "2024-01-02",
  "analysis_timestamp": "2024-01-02T09:30:00Z",
  "volatility_adjustment": 1.0,
  "debate_quality_score": 7.5,
  "symbol": "AAPL",
  "market_type": "US",
  "insufficient_data": false
}
```

创建 `tests/fixtures/llm_responses/invalid_format_response.txt`：
```
I think Apple looks good. You should probably buy it. The stock has been going up lately and the fundamentals seem solid. My recommendation is bullish.
```

**P0-T8：安装依赖并验证原版框架**
```bash
pip install -r requirements.txt
python -c "from tradingagents.graph.trading_graph import TradingAgentsGraph; print('✓ TradingAgents 原版可导入')"
```

**P0-T9：创建阶段状态文件**
```python
# 创建 .pstds_phase.json
import json
state = {
    "current_phase": 1,
    "phase_name": "时间隔离层",
    "completed_phases": [0],
    "phase_0_completed_at": "now"
}
with open(".pstds_phase.json", "w") as f:
    json.dump(state, f, indent=2, ensure_ascii=False, default=str)
```

---

## Phase 0 完成门槛

```bash
# 以下命令必须全部成功（无错误输出）
python -c "from tradingagents.graph.trading_graph import TradingAgentsGraph; print('✓')"
python -c "import pydantic, pymongo, streamlit, plotly, yfinance, akshare; print('✓ 依赖包正常')"
python -c "import yaml; yaml.safe_load(open('config/default.yaml')); print('✓ 配置文件合法')"
ls pstds/temporal/ pstds/data/adapters/ pstds/agents/ pstds/backtest/ && echo "✓ 目录结构正确"
ls tests/fixtures/news/mixed_dates.json tests/fixtures/llm_responses/valid_trade_decision.json && echo "✓ Fixture 文件存在"
docker compose ps | grep mongodb | grep healthy && echo "✓ MongoDB 运行正常"
```
