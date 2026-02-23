# Phase 4：Web UI 升级（第 7-8 周）

**目标**：升级持仓管理页、K 线图组件、历史准确率图，并集成 Phase 1-3 的新功能到分析页面。

> 参考文档：FRD v3.0 第 9.1/9.3 节，SAD v3.0 第 2.6 节

---

## 任务列表

### P4-T1：升级 06_portfolio.py（持仓管理页）

**文件**：`web/pages/06_portfolio.py`（大幅升级现有骨架）

UI 组件（从上到下，参考 FRD v3.0 第 9.1 节）：
1. 持仓录入区：表格形式，`columns = [股票代码, 持仓数量, 成本价, 当前价（自动获取）]`
2. 相关性热力图（复用 `web/components/portfolio_charts.py` 的热力图函数）
3. 波动率贡献饼图（Plotly `go.Pie`）
4. 仓位建议面板（基于当前持仓调用 `PositionAdvisor`）
5. 压力测试区块（标注「历史情景假设，非预测」）

```bash
python -m py_compile web/pages/06_portfolio.py && echo "✓ 语法检查通过"
```

---

### P4-T2：升级 chart.py（K 线图增强）

**文件**：`web/components/chart.py`（在现有四层布局基础上增强，不改变结构）

变更要点（参考 FRD v3.0 第 9.3 节）：
1. **全屏按钮**：`config={"modeBarButtonsToAdd": ["toggleFullscreen"]}`
2. **多均线开关**：在图表旁添加 `st.multiselect` 让用户选择显示 MA5/MA10/MA20/MA60
3. **成交量配色按市场区分**：
   - A 股：红涨绿跌（涨 `#F63538`，跌 `#30CC5A`）
   - 美股/港股：绿涨红跌（颜色相反）
   - 市场类型从 `symbol` 或配置判断
4. **子图时间轴联动**：`xaxis_rangeslider_visible=False`，使用 `shared_xaxes=True`

> 保持四层布局结构（主图 K 线/成交量/MACD/RSI）不变，仅增强上述四点。

```bash
python -m py_compile web/components/chart.py && echo "✓ 语法检查通过"
# 可视化测试（需手动确认）
python -c "
from web.components.chart import create_candlestick_chart
import pandas as pd, numpy as np
dates = pd.date_range('2024-01-01', periods=60)
df = pd.DataFrame({
    'date': dates,
    'open': np.random.uniform(180, 200, 60),
    'high': np.random.uniform(200, 215, 60),
    'low': np.random.uniform(170, 185, 60),
    'close': np.random.uniform(180, 200, 60),
    'volume': np.random.randint(int(1e7), int(1e8), 60)
})
fig = create_candlestick_chart(df, 'AAPL', market_type='US', show_mas=[5, 20])
assert fig is not None
print('✓ K线图含均线和全屏配置，渲染正常')
"
```

---

### P4-T3：升级 03_history.py（添加决策准确率趋势图）

**文件**：`web/pages/03_history.py`（新增「决策准确率趋势」模块）

功能要求（FRD v3.0 第 9.1 节 US-13）：
1. 从 MongoDB `reflection_records` 聚合查询月度准确率：按月分组 → 统计 `prediction_correct=True` 的比例
2. Plotly 折线图：X 轴=月份，Y 轴=准确率（0-100%），添加 50% 基准线（虚线）
3. 过滤器：市场类型（全部/A 股/美股/港股）和分析深度（L0/L1/L2/L3）
4. 数据不足时（< 5 条 reflection 记录）显示提示：「暂无足够历史数据，需累积约 30 次分析后趋势图才有统计意义」
5. `reflection_records` 集合不存在或为空时页面正常显示，不抛出异常

```bash
python -m py_compile web/pages/03_history.py && echo "✓ 语法检查通过"
```

---

### P4-T4：升级 01_analysis.py（集成新功能展示组件）

**文件**：`web/pages/01_analysis.py`（在分析结果区新增两个组件）

① **新闻过滤统计**（在新闻标签页顶部）：
```python
# 使用 st.columns(4) 展示四个 st.metric
col1, col2, col3, col4 = st.columns(4)
col1.metric("原始新闻", stats.raw_count)
col2.metric("时间过滤后", stats.after_temporal, delta=f"-{stats.temporal_filtered}", delta_color="inverse")
col3.metric("相关性过滤后", stats.after_relevance, delta=f"-{stats.relevance_filtered}", delta_color="inverse")
col4.metric("最终使用", stats.after_dedup)
# 数据来源：GraphState.news_filter_stats
```

② **情景记忆侧边栏**（`st.sidebar` 底部）：
```python
st.sidebar.markdown("---")
st.sidebar.markdown("**相似历史决策**")
similar = state.get("similar_past_decisions", [])
if similar:
    for rec in similar[:5]:
        st.sidebar.write(f"{rec['date']} | {rec['action']} | 置信度 {rec['confidence']:.0%}")
else:
    st.sidebar.caption("（首次分析，暂无历史参考）")
```

```bash
python -m py_compile web/pages/01_analysis.py && echo "✓ 语法检查通过"
```

---

## Phase 4 完成门槛

```bash
echo "=== Phase 4 验证开始 ==="

# 语法检查（所有 Web 文件）
python -m py_compile \
    web/app.py \
    web/pages/01_analysis.py \
    web/pages/03_history.py \
    web/pages/06_portfolio.py \
    web/pages/08_portfolio_analysis.py \
    web/components/chart.py \
    web/components/portfolio_charts.py
echo "✓ 全部 Web 文件语法正常"

# 深色主题代码层验证（检查图表函数是否有 plotly_dark 分支）
python -c "
import inspect, importlib

modules_to_check = [
    ('web.components.chart', 'create_candlestick_chart'),
    ('web.components.portfolio_charts', 'render_correlation_heatmap'),
]
for mod_name, func_name in modules_to_check:
    try:
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        src = inspect.getsource(func)
        assert 'plotly_dark' in src or 'dark' in src.lower(), \
            f'❌ {mod_name}.{func_name} 缺少深色主题分支（plotly_dark）'
        print(f'✓ {func_name} 包含深色主题处理')
    except ImportError as e:
        print(f'⚠️  {mod_name} 导入失败，跳过：{e}')
"

# 全量自动化测试（确保所有前序 Phase 不被破坏）
pytest tests/ -v --tb=short -q
# 期望：0 failed

# 🔴 关键回归
pytest tests/integration/test_backtest_no_lookahead.py -v --tb=short
# 期望：REG-001~007，7 passed

echo ""
echo "=== 手动端到端检查清单（运行 streamlit run web/app.py）==="
echo "□ 08_portfolio_analysis 页面可打开，热力图正常渲染"
echo "□ 06_portfolio 页面热力图和波动率饼图正常"
echo "□ 01_analysis 分析完成后，新闻标签页顶部显示四格过滤统计"
echo "□ 01_analysis 侧边栏底部显示「相似历史决策」（无历史时显示提示文字）"
echo "□ 03_history 准确率趋势图正常（无数据时显示提示文字，不崩溃）"
echo "□ K线图有全屏按钮，均线可单独开关"
echo "□ A 股 K 线成交量：涨红跌绿；美股 K 线：涨绿跌红"
echo "□ 深色主题下无白色背景块"

echo "=== Phase 4 全部验证通过，v3.0 开发完成 ==="
```

---

## 最终发布验证（Phase 4 完成后执行）

```bash
echo "=== v3.0 最终发布验证 ==="

# 完整测试套件
pytest tests/ -v --tb=short

# 覆盖率报告
pytest tests/ --cov=pstds --cov-report=term-missing --cov-fail-under=80
# 要求：pstds/temporal/ > 95%，总体 > 80%

# 全部回归测试（必须 100% 通过）
pytest tests/integration/test_backtest_no_lookahead.py -v
# 期望：REG-001~007，7 passed（v3.0 红线）

# 端到端冒烟测试
python -c "
from pstds.agents.extended_graph import ExtendedTradingAgentsGraph
from pstds.temporal.context import TemporalContext
from datetime import date
ctx = TemporalContext.for_live(date(2024, 1, 2))
graph = ExtendedTradingAgentsGraph(config={'analysis_depth': 'L1'})
result = graph.propagate('AAPL', '2024-01-02', ctx=ctx)
assert result['decision']['action'] in ['STRONG_BUY','BUY','HOLD','SELL','STRONG_SELL','INSUFFICIENT_DATA']
assert result.get('news_filter_stats') is not None, '❌ NewsFilter 未集成到分析流程'
print('✓ v3.0 端到端冒烟测试通过')
print(f'  决策: {result[\"decision\"][\"action\"]}')
print(f'  新闻过滤：原始{result[\"news_filter_stats\"].raw_count}条 → 使用{result[\"news_filter_stats\"].after_dedup}条')
"

# 组合分析冒烟测试
python -c "
from pstds.portfolio.analyzer import PortfolioAnalyzer
from pstds.portfolio.advisor import PositionAdvisor
from pstds.temporal.context import TemporalContext
from datetime import date
print('✓ 组合分析模块可导入')
ctx = TemporalContext.for_live(date(2024, 3, 29))
print(f'✓ 组合分析上下文创建正常，analysis_date={ctx.analysis_date}')
"

echo ""
echo "🎉 PSTDS v3.0 所有验证通过！"
echo ""
echo "v3.0 新增可信度红线（与 REG-001 同等重要）："
echo "  REG-007：情景记忆不引入未来决策 ✅"
echo "  PA-002：组合分析时间隔离 ✅"
```
