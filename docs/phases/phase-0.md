# Phase 0：编码前验证

**目标**：确认 v1.0 Code Review 的 9 项 Bug 修复全部生效，所有现有测试通过，再开始 v3.0 新功能开发。

> ⚠️ **这是 v3.0 的起点。不要在现有测试失败的情况下添加任何新代码。**

---

## 任务列表

**P0-T1：激活环境并验证起点状态**
```bash
cd /path/to/pstds
source .venv/bin/activate

# 运行全部现有测试
pytest tests/ -v --tb=short

# 期望结果：
# TG-001~TG-012（TemporalGuard）✅
# PM-001~PM-008（Pydantic 模型）✅
# RT-001~RT-008（市场路由器）✅
# YF-001~YF-005（YFinance 适配器）✅
# AK-001~AK-005（AKShare 适配器）✅
# INT-001~INT-007（集成测试）✅
# REG-001~REG-005（前视偏差回归）✅
```

**P0-T2：验证 M1 修复（temporal_injection monkey-patch）**
```bash
# 验证 TemporalContext 注入机制存在且正常工作
python -c "
from pstds.agents.temporal_injection import inject_temporal_context, restore_original_router
import tradingagents.dataflows.interface as iface
from pstds.temporal.context import TemporalContext
from datetime import date

original = iface.route_to_vendor
ctx = TemporalContext.for_backtest(date(2024, 1, 2))

inject_temporal_context(ctx)
assert iface.route_to_vendor is not original, '❌ BUG-002 未修复：注入失败'
print('✓ temporal_injection 注入正常')

restore_original_router()
assert iface.route_to_vendor is original, '❌ BUG-002 修复有问题：恢复失败'
print('✓ temporal_injection 恢复正常')
"
```

**P0-T3：验证 M3 修复（回测使用真实价格数据，非随机 mock）**
```bash
python -c "
import inspect
from pstds.backtest.runner import BacktestRunner
runner = BacktestRunner()
# 确认 _get_mock_prices 已被替换为真实数据获取
assert hasattr(runner, '_get_real_prices'), '❌ BUG-003 未修复：_get_real_prices 方法不存在'
src = inspect.getsource(runner._get_real_prices)
assert 'random' not in src.lower() and 'mock' not in src.lower(), '❌ BUG-003 未修复：_get_real_prices 仍包含 random/mock 逻辑'
print('✓ 回测引擎使用真实价格数据')
"
```

**P0-T4：验证 L5 修复（新闻时区统一 UTC）**
```bash
python -c "
import inspect
from pstds.data.adapters.yfinance_adapter import YFinanceAdapter
src = inspect.getsource(YFinanceAdapter.get_news)
assert 'tzinfo' in src or 'utc' in src.lower() or 'UTC' in src, '❌ L5 未修复：get_news 仍使用 naive datetime（无时区信息）'
assert 'tz=None' not in src, '❌ L5 未修复：get_news 仍使用 tz=None'
print('✓ 新闻时间戳使用 UTC')
"
```

**P0-T5：验证阶段状态文件**
```bash
python -c "
import json, os
if not os.path.exists('.pstds_phase.json'):
    state = {'current_phase': 1, 'phase_name': '功能补全', 'completed_phases': [0]}
    json.dump(state, open('.pstds_phase.json', 'w'), indent=2, ensure_ascii=False)
    print('✓ 创建阶段状态文件')
else:
    s = json.load(open('.pstds_phase.json'))
    print(f'✓ 阶段状态文件存在，当前: Phase {s[\"current_phase\"]}')
"
```

---

## Phase 0 完成门槛

```bash
echo "=== Phase 0 验证 ==="

# 1. 全套测试通过（零失败）
pytest tests/ --tb=short -q
# 期望：X passed, 0 failed

# 2. 覆盖率满足基线
pytest tests/ --cov=pstds/temporal --cov-fail-under=95 -q
# 期望：pstds/temporal/ 覆盖率 > 95%

# 3. 关键阻塞性用例
pytest tests/unit/test_temporal_guard.py::test_future_timestamp_raises -v      # TG-003
pytest tests/integration/test_backtest_no_lookahead.py::test_reg001_aapl_lookahead_elimination -v  # REG-001
pytest tests/integration/test_backtest_no_lookahead.py::test_reg003_backtest_blocks_realtime_api -v # REG-003

echo "=== Phase 0 通过，可进入 Phase 1 ==="
```

> 若任何现有测试失败，先修复再继续。Phase 0 是 v3.0 所有新功能的基础，基础不稳不得前进。
