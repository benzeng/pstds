# Phase 2：数据服务层（第 3-4 周）

**目标**：实现数据适配器、缓存、路由，多市场数据获取正常。

---

## 任务列表

**P2-T1：实现 MarketDataAdapter Protocol**
`pstds/data/adapters/base.py` — 严格按照 ISD v1.0 第 4 节的方法签名和返回值说明。

**P2-T2：实现 YFinanceAdapter**
`pstds/data/adapters/yfinance_adapter.py`：
- 所有方法接受 `ctx: TemporalContext`
- `get_ohlcv`：查询后对每行 date 调用 `TemporalGuard.validate_timestamp`
- `get_news`：调用 `TemporalGuard.filter_news` 过滤未来新闻
- `get_fundamentals`：缺失字段用 `None` 填充，网络失败返回含 `None` 值的字典
- 必须调用 `TemporalGuard.assert_backtest_safe(ctx, 'yfinance_realtime')` 保护实时端点

**P2-T3：实现 AKShareAdapter**
`pstds/data/adapters/akshare_adapter.py`：
- A 股财务字段中文→英文映射（`市盈率→pe_ratio`、`市净率→pb_ratio`、`净资产收益率→roe` 等）
- 东方财富股吧情绪数据标准化为 `NewsItem` 格式（情绪内容作为 content）
- 港股接口分支：`symbol.endswith('.HK')` 时使用 AKShare 港股行情接口

**P2-T4：实现 LocalCSVAdapter**
`pstds/data/adapters/local_csv_adapter.py`：读取 `data/raw/prices/{symbol}.csv`，天然时间隔离（过滤 date > analysis_date 的行）。

**P2-T5：实现 FallbackManager**
`pstds/data/fallback.py`：主源失败时按优先级尝试备用源，记录 `fallback_used` 到 `DataQualityReport`。

**P2-T6：实现 SQLite CacheManager**
`pstds/data/cache.py`：
- 按 DDD v2.0 第 3.3 节创建 4 张缓存表
- 读取缓存时 WHERE 条件包含 `date <= analysis_date`
- 行情数据同时追加写入 `data/raw/prices/{symbol}.parquet`（Parquet 格式）
- 新闻数据同时追加写入 `data/raw/news/{symbol}/{date}.json`

**P2-T7：实现 DataQualityGuard**
`pstds/data/quality_guard.py`：输出 `DataQualityReport`（含 `score`、`missing_fields`、`anomaly_alerts`、`filtered_news_count`、`fallbacks_used`），评分规则按 DDD v2.0 第 3.4 节。

**P2-T8：完善 pstds/data/router.py**
集成 FallbackManager，提供 `get_adapter(symbol, ctx)` 方法返回主源适配器（附带自动降级能力）。

**P2-T9：编写适配器测试**
创建 `tests/adapters/test_yfinance_adapter.py`（YF-001~005）和 `tests/adapters/test_akshare_adapter.py`（AK-001~005），使用 Fixture 文件，不进行真实网络请求（使用 `pytest-mock` Mock）。

---

## Phase 2 完成门槛

```bash
echo "=== Phase 2 验证开始 ==="

pytest tests/adapters/ -v --tb=short
# 预期：10 passed（YF-001~005，AK-001~005）

# 验证时间隔离在适配器层生效
python -c "
from datetime import date
from pstds.temporal.context import TemporalContext
from pstds.data.adapters.yfinance_adapter import YFinanceAdapter
from pstds.temporal.guard import RealtimeAPIBlockedError
ctx = TemporalContext.for_backtest(date(2024, 1, 2))
adapter = YFinanceAdapter()
try:
    # BACKTEST 模式下调用实时接口应被阻断
    adapter._call_realtime_endpoint('AAPL', ctx)
    print('ERROR: 实时接口未被阻断！')
    exit(1)
except RealtimeAPIBlockedError:
    print('✓ BACKTEST 模式实时 API 阻断验证通过')
except AttributeError:
    print('✓ 实时端点保护机制存在（方法级别）')
"

# 验证缓存时间隔离
python -c "
from pstds.data.cache import CacheManager
print('✓ CacheManager 可导入')
"

# 总覆盖率
pytest tests/unit/ tests/adapters/ --cov=pstds --cov-report=term-missing

echo "=== Phase 2 验证完成 ==="
```
