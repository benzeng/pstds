# Phase 3：组合分析模块（第 5-6 周）

**目标**：实现 PortfolioAnalyzer、PositionAdvisor、PortfolioCoordinator 和对应的 Web 页面。

> 参考文档：DDD v3.0 第 2.2 节，ISD v2.0 第 4.2/4.3 节，FRD v3.0 第 9.1/9.2 节
>
> ⚠️ **时间隔离是本 Phase 的最高优先级**：所有 `get_ohlcv` 调用必须传入 `ctx`，`end_date` 不得超过 `ctx.analysis_date`（约束 C-09）。

---

## 任务列表

### P3-T1：实现 PortfolioAnalyzer

**文件**：`pstds/portfolio/analyzer.py`

接口规范（严格按照 ISD v2.0 第 4.2 节）：

```python
class PortfolioAnalyzer:
    def __init__(self, data_router, config: dict): ...

    def correlation_matrix(
        self,
        symbols: List[str],
        ctx: TemporalContext,
        min_common_days: int = 30,
    ) -> Optional[pd.DataFrame]:
        # 从 DataRouter 获取各股 OHLCV，end_date 强制为 ctx.analysis_date
        # 计算日收益率（pct_change），然后 DataFrame.corr()（Pearson）
        # 共同交易日 < min_common_days 时返回 None，记录 E011 警告

    def hhi(self, weights: Dict[str, float]) -> float:
        # sum(w^2)，纯计算函数，无需 ctx

    def volatility_contribution(
        self, symbols: List[str], weights: Dict[str, float], ctx: TemporalContext
    ) -> Dict[str, float]:
        # 边际风险贡献法（marginal contribution × weight / portfolio_vol）
        # 返回：symbol → 贡献百分比，所有值之和 = 100%

    def stress_test(
        self, symbols: List[str], weights: Dict[str, float], ctx: TemporalContext
    ) -> float:
        # 返回：float（负数），表示组合损失比例
        # 各股历史最大单日跌幅（min(pct_change)）加权求和
        # 例：-0.087 表示估算最大损失 8.7%
        # ⚠️ 返回值是 float，不是 Dict，调用方直接用数值展示
```

```bash
# 验证
pytest tests/unit/test_portfolio_analyzer.py -v --tb=short
# 期望：PA-001~PA-007，7 passed

# 🔴 时间隔离专项验证（阻塞性）
pytest tests/unit/test_portfolio_analyzer.py::test_correlation_time_isolation -v  # PA-002
# 期望：PASSED，任何 end_date > ctx.analysis_date 的 OHLCV 请求必须被拒绝
```

---

### P3-T2：实现 PositionAdvisor

**文件**：`pstds/portfolio/advisor.py`

实现 `PositionAdvisor.advise()` 的完整算法（ISD v2.0 第 4.3 节有详细步骤注释）：

1. `ACTION_TO_WEIGHT` 映射（代码中的字典常量，值为直接仓位比例，**不是归一化权重**）：
   ```python
   ACTION_TO_WEIGHT = {
       "STRONG_BUY":  0.20,
       "BUY":         0.12,
       "HOLD":        0.00,
       "SELL":       -0.06,
       "STRONG_SELL": -0.12,
       "INSUFFICIENT_DATA": 0.00,
   }
   ```
2. 调用 `PortfolioAnalyzer.correlation_matrix()` 和 `hhi()`
3. HHI 超限时的缩减算法：识别高相关对（相关性 > 阈值）→ 按比例缩减 → 循环直到 `HHI <= max_hhi`
4. `current_positions` 差值计算 → `operation` 字段（BUY/SELL/HOLD，差值绝对值 < 0.02 视为 HOLD）
5. 保证最终 `sum(adjusted_weights) <= 1.0`

同时实现（严格按照 ISD v2.0 第 2.4/2.5 节，**字段名必须与此完全一致**）：
```python
@dataclass
class PositionAdvice:
    symbol: str
    initial_weight: float        # ACTION_TO_WEIGHT 映射的原始建议仓位（勿用 raw_weight）
    adjusted_weight: float       # 组合约束调整后
    adjustment_reason: str       # 调整原因说明（勿用 reason）
    operation: str               # "BUY" | "SELL" | "HOLD"
    current_weight: Optional[float] = None  # 当前实际持仓比例（用户提供时填充）

@dataclass
class PortfolioImpact:
    original_weight: float
    adjusted_weight: float
    adjustment_reason: str
    high_correlation_pairs: List[Tuple[str, float]] = field(default_factory=list)
    portfolio_hhi: float = 0.0
```

```bash
# 验证
python -c "
from pstds.portfolio.advisor import PositionAdvisor, PositionAdvice, PortfolioImpact
print('✓ PositionAdvisor 和数据模型可导入')
"
```

---

### P3-T3：实现 PortfolioCoordinator

**文件**：`pstds/portfolio/coordinator.py`

`PortfolioCoordinator` 是批量分析的后处理协调器，在所有股票分析完成后调用：

```python
class PortfolioCoordinator:
    def coordinate(
        self,
        decisions: List[TradeDecision],
        current_positions: Dict[str, float],
        ctx: TemporalContext,
    ) -> List[TradeDecision]:
        """
        批量分析后处理协调器。
        副作用：将 portfolio_snapshot 写入 MongoDB portfolio_snapshots 集合。
        步骤：
        1. 调用 PortfolioAnalyzer 计算相关性矩阵
        2. 调用 PositionAdvisor 获取调整后仓位建议
        3. 将 PortfolioImpact 回填到每个 TradeDecision.portfolio_impact 字段
        4. 构造 portfolio_snapshot dict 写入 MongoDB portfolio_snapshots 集合（副作用）
        返回：更新了 portfolio_impact 字段的 decisions 列表
        """
```

> 单股分析不经过 PortfolioCoordinator，`portfolio_impact` 保持 `None`。
> 批量分析入口在 `ExtendedTradingAgentsGraph.propagate_batch()` 中调用 Coordinator。

---

### P3-T4：实现组合分析 Web 页面

**文件**：`web/pages/08_portfolio_analysis.py`（新建），提取公共组件到 `web/components/portfolio_charts.py`

UI 组件（从上到下，参考 FRD v3.0 第 9.2 节）：
1. 多股票代码输入框（`st.text_area`，逗号分隔，说明最多 20 只）
2. 时间窗口选择器（`st.selectbox`：30/60/90/180 天）
3. 分析按钮，点击后调用 `PortfolioAnalyzer`
4. 相关性热力图（Plotly `go.Heatmap`）：
   - `colorscale="RdBu_r"`（红=高相关，蓝=低/负相关）
   - 相关系数 > 0.7 的格子添加矩形注释标记
   - 悬停显示精确系数值（小数点后 2 位）
5. 仓位建议面板：展示 `PositionAdvice` 列表，`st.progress` 可视化仓位比例
6. 压力测试结果（明确标注「历史情景假设，非预测」）

> 图表使用 Plotly，**不使用 `st.pyplot`**（避免静态图）。
> 提取热力图和仓位面板为 `web/components/portfolio_charts.py` 中的可复用函数，供 06 和 08 两个页面共用。

```bash
# 验证
python -m py_compile web/pages/08_portfolio_analysis.py && echo "✓ 语法检查通过"
```

---

## Phase 3 完成门槛

```bash
echo "=== Phase 3 验证开始 ==="

# 组合分析单元测试
pytest tests/unit/test_portfolio_analyzer.py -v --tb=short
# 期望：PA-001~PA-007，7 passed

# 🔴 时间隔离回归（阻塞性）
pytest tests/unit/test_portfolio_analyzer.py::test_correlation_time_isolation -v  # PA-002

# 组合分析集成测试
pytest tests/integration/test_portfolio_flow.py -v --tb=short
# 期望：PA-INT-001~PA-INT-004，4 passed

# 🔴 组合时间隔离专项（阻塞性）
pytest tests/integration/test_portfolio_flow.py::test_portfolio_temporal_isolation -v

# 全量回归（确保前序 Phase 不被破坏）
pytest tests/integration/test_backtest_no_lookahead.py -v --tb=short
# 期望：REG-001~007，7 passed

# 页面语法检查
python -m py_compile web/pages/08_portfolio_analysis.py web/components/portfolio_charts.py

echo "=== Phase 3 全部验证通过，可进入 Phase 4 ==="
```

**Phase 3 阻塞条件**：PA-002（`correlation_matrix` 使用了 `analysis_date` 之后的价格）失败，立即停止。这与 REG-001 属于同等级别的前视偏差错误。
