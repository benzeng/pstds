# PSTDS 代码 Review 报告

> 项目：Personal Stock Trading Decision System (pstds-main)  
> Review 日期：2026-02-22  
> 代码规模：~50 个 Python 文件，约 5000+ 行

---

## 一、总体评价

PSTDS 是一个基于 LLM + Multi-Agent 架构的个人股票辅助决策系统，整体设计思路清晰，模块化程度较高。代码中有不少值得肯定的实践，同时也存在若干需要关注和改进的问题。

**亮点：**
- 时间隔离（Temporal Isolation）设计扎实，是该系统最核心的工程亮点
- 适配器模式 + 降级管理（FallbackManager）设计合理
- Pydantic 输出校验机制完善
- 配置分层（default.yaml + user.yaml 深度合并）

**主要风险：**
- 安全漏洞：API Key 明文写入配置文件并提交到仓库
- 数据竞争：`execute_with_confidence` 等方法临时修改共享状态存在线程安全问题
- 错误处理过于宽泛，静默吞掉异常
- 回测绩效指标中胜率/准确率存在计算逻辑缺陷

---

## 二、严重问题（必须修复）

### 🔴 [S1] API Key 明文写入配置文件

**位置：** `config/default.yaml`

```yaml
api_keys:
  alpha_vantage: VCR9IDXRTZ6XPS4S  # ← 真实 Key 硬编码
```

**问题：** Alpha Vantage API Key 已明文提交到版本库，极易泄露。

**修复方案：**
```yaml
# config/default.yaml
api_keys:
  alpha_vantage: null   # 改为 null，通过环境变量注入
```

```python
# pstds/config.py - get_api_key 方法中增加环境变量回退
def get_api_key(self, service: str) -> Optional[str]:
    # 优先从环境变量读取
    env_key = f"{service.upper()}_API_KEY"
    env_val = os.environ.get(env_key)
    if env_val:
        return env_val
    return self.get(f"api_keys.{service}")
```

同时将 `config/user.yaml` 加入 `.gitignore`。

---

### 🔴 [S2] `execute_with_confidence` 线程安全问题

**位置：** `pstds/backtest/executor.py`（第 130-150 行附近）

```python
# 当前代码 - 存在竞争条件
original_size = self.position_sizes[action]
self.position_sizes[action] = adjusted_size   # ← 修改共享状态
trade = self.execute(decision, current_price, trade_date)
self.position_sizes[action] = original_size   # ← 恢复，但中间可能被打断
```

若回测以多线程并行执行，两个线程同时修改 `self.position_sizes` 会导致数据竞争。

**修复方案：**
```python
def execute_with_confidence(self, decision, current_price, trade_date):
    action = decision.action
    confidence = decision.confidence
    
    # 计算调整后的 size，不修改共享状态
    if confidence >= 0.8:
        factor = 1.0
    elif confidence >= 0.5:
        factor = 0.8
    else:
        factor = 0.5
    
    base_size = self.position_sizes.get(action, 0.0)
    # 直接传入临时 size，不修改 self.position_sizes
    return self._execute_with_size(decision, current_price, trade_date, base_size * factor)
```

---

### 🔴 [S3] `_append_parquet` 存在数据重复风险

**位置：** `pstds/data/cache.py`

```python
def _append_parquet(self, symbol: str, df: pd.DataFrame) -> None:
    if parquet_path.exists():
        existing_df = pq.read_table(parquet_path).to_pandas()
        df = pd.concat([existing_df, df], ignore_index=True)  # ← 没有去重
    pq.write_table(table, parquet_path)
```

每次追加都会先 read 全量、再 concat、再全量 write，没有对 `(symbol, date)` 去重，会导致：
1. 数据重复累积，文件无限增大
2. 回测时同一天数据被重复计算

**修复方案：**
```python
def _append_parquet(self, symbol: str, df: pd.DataFrame) -> None:
    parquet_path = self.parquet_dir / f"{symbol}.parquet"
    try:
        if parquet_path.exists():
            existing_df = pq.read_table(parquet_path).to_pandas()
            combined = pd.concat([existing_df, df], ignore_index=True)
            # 按 (symbol, date) 去重，保留最新记录
            combined = combined.drop_duplicates(subset=["date"], keep="last")
            df = combined
        table = pa.Table.from_pandas(df)
        pq.write_table(table, parquet_path)
    except Exception as e:
        # 记录到 logger 而非 print
        logger.error(f"Error appending Parquet for {symbol}: {e}")
```

---

## 三、重要问题（强烈建议修复）

### 🟠 [M1] Monkey-patch 方式注入 TemporalContext 脆弱且危险

**位置：** `pstds/agents/extended_graph.py` - `_inject_ctx_to_agents()`

```python
# 通过模块级变量 monkey-patch
for mod in self._patched_modules:
    mod.route_to_vendor = _guarded_route
```

**问题：**
- 多实例并发时，所有实例共享同一个模块级 `route_to_vendor`，会相互覆盖
- 若 `propagate()` 中途抛异常且 `finally` 未执行，patch 永久生效，影响后续所有调用
- 代码注释中自己也标注了 `BUG-002`，说明是已知问题

**推荐方案：** 将 `TemporalContext` 通过依赖注入传入数据层，而非在调用时 patch 全局函数。若短期内无法重构，至少加 threading.Lock 防止并发覆盖。

---

### 🟠 [M2] `clear_expired` 中 `decision_hash_cache` TTL 单位不一致

**位置：** `pstds/data/cache.py` - `clear_expired()`

```python
tables = [
    ("ohlcv_cache",         "fetched_at", "ttl_hours"),
    ("fundamentals_cache",  "fetched_at", "ttl_hours"),
    ("news_cache",          "fetched_at", "ttl_hours"),
    ("technical_cache",     "fetched_at", "ttl_hours"),
    ("decision_hash_cache", "created_at", "ttl_days"),  # ← ttl_days 单位是天
]

# 但清理 SQL 用同一个模板，单位全按"小时"处理：
cursor.execute(f"""
    DELETE FROM {table}
    WHERE datetime({time_col}) < datetime('now', '-' || {ttl_col} || ' hours')
""")
```

`decision_hash_cache.ttl_days = 7` 会被当作 7 小时处理，7 天的缓存实际上只保留 7 小时。

**修复方案：**
```python
# 拆分两个 SQL，分别处理 hours 和 days
for table, time_col, ttl_col, unit in tables:
    cursor.execute(f"""
        DELETE FROM {table}
        WHERE datetime({time_col}) < datetime('now', '-' || {ttl_col} || ' {unit}')
    """)
```

---

### 🟠 [M3] 胜率计算逻辑错误

**位置：** `pstds/backtest/performance.py` - `calculate_with_trades()`

```python
for trade in trades:
    if trade.get("action") == "sell":
        buy_price = None
        for t in trades:  # ← O(n²) 且只找第一条 buy，不区分 symbol
            if t.get("symbol") == trade.get("symbol") and t.get("action") == "buy":
                buy_price = t.get("price")
                break
```

问题：
1. 对同一 symbol 多次买卖，只取第一条 buy 记录作参考价，后续买入价被忽略
2. 时间顺序未考虑，可能用"未来的买入价"匹配"更早的卖出"
3. O(n²) 复杂度，交易量大时性能差

**修复方案：** 用 FIFO 栈或按 symbol 分组的买卖队列来正确匹配买卖对。

---

### 🟠 [M4] `AuditLogger` 在 `filter_news` 循环中每次都实例化

**位置：** `pstds/temporal/guard.py`

```python
for news in news_list:
    ...
    logger = AuditLogger()   # ← 每条新闻都 new 一个 logger 实例
    logger.log(...)
```

如果 `AuditLogger.__init__()` 涉及文件 I/O（打开日志文件），每条新闻都实例化一次会产生大量不必要的文件操作。

**修复方案：** 将 logger 提升到循环外，或使用模块级单例。

---

### 🟠 [M5] `validate_output_with_retry` 重试无法真正触发 LLM 重新生成

**位置：** `pstds/agents/extended_graph.py`

```python
while self.output_validation_retries < self.max_output_retries:
    try:
        data = json.loads(llm_output)     # ← llm_output 固定，永远是同一个字符串
        trade_decision = TradeDecision(...)
        trade_decision.model_validate(trade_decision)
        return trade_decision
    except (json.JSONDecodeError, ValidationError) as e:
        self.output_validation_retries += 1
        print(f"Retrying... ({self.output_validation_retries}/{self.max_output_retries})")
```

`llm_output` 在整个重试循环中保持不变，格式错误时重试只是重复尝试同一段文本，没有意义。真正的重试应重新调用 LLM 并要求格式修正。

---

## 四、一般问题（建议改进）

### 🟡 [L1] 大量使用 `print()` 代替日志系统

整个项目中充斥着 `print(f"...")` 调用，包括关键错误路径：

```python
# FallbackManager、MongoStore、CacheManager 等处均有
print(f"Primary adapter {adapter.name} failed: {e}")
print(f"MongoDB 插入失败: {e}")
except Exception as e:
    print(f"Error appending to Parquet: {e}")
```

`print` 无法按级别过滤、无法写入日志文件、无法在生产环境关闭。建议统一改用 `logging` 模块，配合项目已有的 `logging.basicConfig` 配置。

---

### 🟡 [L2] `pstds/data/router.py` 中导入路径错误

```python
# DataRouter.__init__ 中
from pstds.fallback import FallbackManager  # ← 路径错误

# get_fallback_manager 中也重复导入
from pstds.fallback import FallbackManager  # ← 同样错误
```

文件实际位置是 `pstds/data/fallback.py`，正确导入路径应为：
```python
from pstds.data.fallback import FallbackManager
```

这是一个会在运行时导致 `ImportError` 的问题。

---

### 🟡 [L3] `get_ohlcv` 缓存过期逻辑未生效

**位置：** `pstds/data/cache.py`

```python
def get_ohlcv(self, symbol, start_date, end_date, ctx):
    ...
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        return df   # ← 直接返回，未检查 fetched_at 是否过期
    return None
```

对比 `get_fundamentals()` 中正确检查了 `_is_expired()`，`get_ohlcv` 忘记了同样的检查，导致 OHLCV 数据永不过期。

---

### 🟡 [L4] `DataQualityGuard` 实例状态未隔离

**位置：** `pstds/data/quality_guard.py`

```python
class DataQualityGuard:
    def __init__(self):
        self.report = DataQualityReport()  # ← 单实例共享

    def validate_ohlcv(self, df, symbol, ctx):
        ...
        return self.report   # 每次调用都累积到同一个 report
```

如果同一个 `DataQualityGuard` 实例对多个 symbol 调用 `validate_ohlcv`，异常会跨 symbol 累积，导致报告数据混乱。每次验证应使用独立的 `DataQualityReport` 实例，或者在每次验证前调用 `reset()`。

---

### 🟡 [L5] `MarketRouter` A股代码识别不完整

**位置：** `pstds/data/router.py`

```python
CN_A_PREFIXES = {"60", "00", "30", "68", "83", "43"}
```

缺少部分 A股主板和科创板代码前缀：
- `688xxx`（科创板）— 前两位 "68" 已包含，但 `688` 系列开头是 "68" ✓
- `001xxx`（深交所主板新股）— "00" 已包含 ✓  
- `920xxx`（北交所新股）— 前两位 "92" 未包含

建议补充 `"92"` 并关注北交所代码段的持续变化。

---

### 🟡 [L6] pyproject.toml 中项目名与包名不一致

```toml
[project]
name = "tradingagents"   # ← 上游项目名

[tool.setuptools.packages.find]
include = ["tradingagents*", "cli*"]  # ← 没有包含 pstds 包
```

`pstds` 是本项目的核心自研包，但 `pyproject.toml` 中并未包含，导致 `pip install .` 后 `import pstds` 会失败。

**修复方案：**
```toml
[project]
name = "pstds"

[tool.setuptools.packages.find]
include = ["tradingagents*", "cli*", "pstds*", "web*"]
```

---

### 🟡 [L7] 回测 `calculate_with_trades` 胜率计算未考虑时间顺序

（见 M3，此处补充）此外，代码注释中提到的 7 项绩效指标中，`win_rate` 和 `prediction_accuracy` 在基本 `calculate()` 方法中直接返回 `0.0` 占位，对调用者不够透明，建议改为 `None` 或加说明注释，避免误导。

---

## 五、代码规范问题

| 问题 | 位置 | 说明 |
|------|------|------|
| `any` 用作类型注解 | `router.py` `get_adapter()` 返回值 | 应使用 `Any`（大写）或具体类型 |
| 测试文件散落根目录 | `test.py`, `test_akshare_comprehensive.py` 等 | 应移入 `tests/` 目录统一管理 |
| `main.py` 与 `start.py` 功能重叠 | 根目录 | 入口文件冗余，建议合并 |
| `config/user.yaml` 已包含真实配置 | 根目录 | 不应提交到版本库，加入 `.gitignore` |
| 文档注释中有英文 `any` 类型 | 多处 | 保持类型注解风格一致 |

---

## 六、架构与设计建议

### 1. 时间隔离层（核心亮点，建议加固）

时间隔离是 PSTDS 最重要的特性，现有实现已相当完善（`TemporalContext` 不可变、`TemporalGuard` 校验、审计日志）。建议进一步：
- 在 `DataRouter.get_adapter()` 签名中强制要求传入 `ctx` 参数（目前是 `Optional`）
- 为关键数据路径添加集成测试，验证回测模式下不会泄漏未来数据

### 2. 两套系统的集成方式

`pstds/` 与 `tradingagents/` 的集成目前依赖 monkey-patch（见 M1），这是一个明显的技术债。长期建议将 `TemporalContext` 作为 `TradingAgentsGraph` 的一等公民参数，而不是在 `ExtendedTradingAgentsGraph` 中绕过它。

### 3. 并发安全

如果计划在回测中并行多个 symbol 分析（通过 `ThreadPoolExecutor`），需要系统性检查所有共享状态。当前已知问题包括 S2（executor 状态）和 M1（module-level patch）。

### 4. 缺乏集成测试覆盖关键路径

`tests/` 目录下有单元测试，但核心的端到端路径（例如：分析请求 → 数据获取 → 时间隔离校验 → LLM 决策 → 结果存储）缺乏集成测试。建议至少补充：
- 回测无前视偏差验证（已有 `test_backtest_no_lookahead.py`，但需确认覆盖 monkey-patch 路径）
- MongoDB 和 SQLite 缓存协同工作的集成测试

---

## 七、问题优先级汇总

| 级别 | 编号 | 问题描述 |
|------|------|----------|
| 🔴 严重 | S1 | API Key 明文写入配置并提交版本库 |
| 🔴 严重 | S2 | executor 临时修改共享状态存在线程安全问题 |
| 🔴 严重 | S3 | Parquet 追加写入无去重，数据重复累积 |
| 🟠 重要 | M1 | Monkey-patch 注入 TemporalContext 多并发不安全 |
| 🟠 重要 | M2 | `clear_expired` 中 `decision_hash_cache` TTL 单位 bug |
| 🟠 重要 | M3 | 胜率计算逻辑错误（只取第一条 buy 记录） |
| 🟠 重要 | M4 | AuditLogger 在循环中重复实例化 |
| 🟠 重要 | M5 | validate_with_retry 重试无法触发 LLM 重新生成 |
| 🟡 建议 | L1 | 大量 print() 应替换为 logging |
| 🟡 建议 | L2 | `pstds/data/router.py` 导入路径错误（运行时报错） |
| 🟡 建议 | L3 | OHLCV 缓存过期检查缺失 |
| 🟡 建议 | L4 | DataQualityGuard 实例状态跨 symbol 混污 |
| 🟡 建议 | L5 | 北交所代码段未覆盖 |
| 🟡 建议 | L6 | pyproject.toml 未包含 pstds 包 |

---

*Review 结束。如需针对某个模块做更深入的分析，欢迎进一步讨论。*
