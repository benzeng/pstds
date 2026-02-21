# Phase 6：收尾与 v1.0 发布（第 13-16 周）

**目标**：报告导出、通知、成本仪表盘、Docker 部署、完整文档。

---

## 任务列表

**P6-T1**：`pstds/export/md_exporter.py` — Markdown 导出
**P6-T2**：`pstds/export/docx_exporter.py` — Word 导出（python-docx，含封面和免责声明）
**P6-T3**：`pstds/export/pdf_exporter.py` — PDF 导出（WeasyPrint）
**P6-T4**：`pstds/notify/desktop.py` 和 `pstds/notify/email_notify.py`
**P6-T5**：`web/pages/05_cost.py` — 成本仪表盘
**P6-T6**：`web/pages/06_portfolio.py` — 持仓管理（可选）
**P6-T7**：`Dockerfile` + 完善 `docker-compose.yml`
**P6-T8**：`start.py` — 一键启动（含 MongoDB 健康检查）
**P6-T9**：`README.md` — 完整安装和使用文档

---

## Phase 6 完成门槛（v1.0 发布标准）

```bash
echo "=== v1.0 发布验证 ==="

# 完整测试套件
pytest tests/ -v --tb=short
# 预期：所有测试通过

# 覆盖率（必须满足最低要求）
pytest tests/ --cov=pstds --cov-report=term-missing --cov-fail-under=80
# pstds/temporal/ 必须 > 95%

# 前视偏差最终回归（必须通过）
pytest tests/integration/test_backtest_no_lookahead.py::test_aapl_lookahead_regression -v
pytest tests/integration/test_backtest_no_lookahead.py::test_backtest_mode_blocks_all_realtime_apis -v
pytest tests/integration/test_backtest_no_lookahead.py::test_decision_reproducibility -v

# Docker 构建
docker compose build && echo "✓ Docker 镜像构建成功"
docker compose up -d
sleep 15
curl -s http://localhost:8501 > /dev/null && echo "✓ Streamlit 正常运行"
docker compose ps | grep mongodb | grep -i healthy && echo "✓ MongoDB 健康"

# 端到端冒烟测试
python -c "
from pstds.agents.extended_graph import ExtendedTradingAgentsGraph
from pstds.temporal.context import TemporalContext
from datetime import date
ctx = TemporalContext.for_live(date(2024, 1, 2))
graph = ExtendedTradingAgentsGraph(config={'analysis_depth': 'L1', 'use_mock_llm': True})
result = graph.propagate('AAPL', '2024-01-02', ctx=ctx)
assert result['decision']['action'] in ['STRONG_BUY','BUY','HOLD','SELL','STRONG_SELL','INSUFFICIENT_DATA']
assert result['decision']['analysis_date'] == '2024-01-02'
assert len(result['decision']['data_sources']) > 0
print('✓ 端到端冒烟测试通过')
print(f'  决策: {result[\"decision\"][\"action\"]}')
print(f'  置信度: {result[\"decision\"][\"confidence\"]}')
"

echo ""
echo "🎉 PSTDS v1.0 所有验证通过！系统可以投入使用。"
echo "   请阅读 README.md 了解使用方式。"
```
