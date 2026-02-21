# Phase 4：Web UI 与基础设施（第 8-10 周）

**目标**：Streamlit 主分析页可用，调度器运行正常，MongoDB 持久化完整。

---

## 任务列表

**P4-T1：实现 MongoDB 持久化层**
`pstds/storage/mongo_store.py`：
- `save_analysis(state: dict) -> str`：序列化 GraphState，写入 analyses 集合，返回 `_id`
- 写入文档必须包含：`temporal`（审计字段）、`input_hash`（SHA-256）、`decision`（结构化 TradeDecision JSON）、`cost`
- `find_by_symbol_date(symbol, date)` / `list_analyses(symbol, limit)` 查询接口

**P4-T2：实现 result_persistence_node**
`pstds/agents/result_saver.py`：作为 LangGraph 最后节点，调用 `MongoStore.save_analysis()`，并更新 ChromaDB 向量记忆。

**P4-T3：实现任务调度器**
`pstds/scheduler/scheduler.py`（APScheduler 封装）和 `pstds/scheduler/task_queue.py`（asyncio 令牌桶队列）。

**P4-T4：实现 Streamlit 主分析页**
`web/pages/01_analysis.py`：按 DDD v2.0 第 5.1 节 8 步交互流程实现。进度条使用节点权重（技术15%/基本面15%/新闻10%/情绪10%/辩论30%/风险10%/决策10%）。

**P4-T5：实现 K 线图组件**
`web/components/chart.py`：Plotly 4 层布局（K线+均线、成交量、MACD、RSI），技术指标全部用 pandas-ta 本地计算。

**P4-T6：实现自选股和历史记录页面**
`web/pages/02_watchlist.py` 和 `web/pages/03_history.py`。

**P4-T7：实现系统设置页**
`web/pages/07_settings.py`：LLM 配置、API Key 管理（写入 OS Keychain，不明文保存）、数据源偏好。

**P4-T8：创建 web/app.py 入口**
多页面导航配置，加载 config/default.yaml + config/user.yaml。

---

## Phase 4 完成门槛

```bash
echo "=== Phase 4 验证开始 ==="

# MongoDB 连接和写入测试
python -c "
from pstds.storage.mongo_store import MongoStore
store = MongoStore()
test_id = store.save_analysis({'symbol': 'TEST', 'analysis_date': '2024-01-02', 'decision': {'action': 'HOLD'}, 'temporal': {}, 'input_hash': 'test123', 'cost': {'total_tokens': 100, 'estimated_usd': 0.001}})
print(f'✓ MongoDB 写入成功，ID: {test_id}')
doc = store.find_by_id(test_id)
assert doc is not None
print('✓ MongoDB 读取成功')
"

# Streamlit 应用语法检查
python -m py_compile web/app.py web/pages/01_analysis.py && echo "✓ Streamlit 应用语法正常"

# 图表组件测试
python -c "
from web.components.chart import create_candlestick_chart
import pandas as pd
import numpy as np
dates = pd.date_range('2024-01-01', periods=30)
df = pd.DataFrame({'date': dates, 'open': np.random.uniform(180, 200, 30),
    'high': np.random.uniform(200, 210, 30), 'low': np.random.uniform(170, 180, 30),
    'close': np.random.uniform(180, 200, 30), 'volume': np.random.randint(1e7, 1e8, 30)})
fig = create_candlestick_chart(df, 'AAPL')
assert fig is not None
print('✓ K线图组件正常')
"

# 回归测试确保 Phase 3 成果不被破坏
pytest tests/integration/test_backtest_no_lookahead.py -v --tb=short

echo "=== Phase 4 验证完成 ==="
```
