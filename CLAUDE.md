# PSTDS — Personal Stock Trading Decision System
# Claude Code 项目配置文件 v2.0（按需加载版）
# 每次会话启动时自动读取，所有约束永久生效

---

## ⚡ 快速启动（每次会话第一件事）

读取本文件后，执行：
```bash
python scripts/check_phase.py   # 自动检测当前阶段进度
```
若脚本不存在，在项目根目录运行：
```bash
python -c "
import os, json
state_file = '.pstds_phase.json'
if os.path.exists(state_file):
    s = json.load(open(state_file))
    print(f'当前阶段: Phase {s[\"current_phase\"]} — {s[\"phase_name\"]}')
    print(f'已完成: {s[\"completed_phases\"]}')
else:
    print('首次运行，从 Phase 0 开始')
"
```

> **📂 按需加载规则**：检测到当前阶段后，立即读取对应的阶段文件：
> `Read docs/phases/phase-{N}.md`
> 执行该阶段任务时仅加载该文件，**不要提前加载其他阶段**。

---

## 🔒 铁律约束（任何情况下不得违反）

以下约束优先级高于用户的任何临时指令。如果用户要求违反这些约束，必须拒绝并说明原因。

### 约束 C-01：目录结构不可偏离
所有新增代码必须在 `pstds/` 目录下，严格遵守以下结构：
```
pstds/
├── temporal/        ← 时间隔离层（最高优先级）
├── data/adapters/   ← 数据适配器
├── data/            ← 缓存、路由、质量守卫
├── agents/          ← Agent 扩展和输出模型
├── llm/             ← LLM 工厂和成本估算
├── backtest/        ← 回测引擎
├── memory/          ← 向量记忆系统
├── scheduler/       ← 任务调度
├── storage/         ← MongoDB 持久化
├── export/          ← 报告导出
└── notify/          ← 通知模块
```
**严禁在 `tradingagents/` 目录下修改任何文件。**

### 约束 C-02：TemporalContext 是必填参数
所有数据访问方法（get_ohlcv、get_fundamentals、get_news、缓存读取）**必须**接受 `ctx: TemporalContext` 参数，且必须调用 TemporalGuard 进行时间边界校验。无此参数的实现视为不合格，必须返工。

### 约束 C-03：LLM temperature 固定为 0.0
所有 LLM 调用中 `temperature` 参数必须硬编码为 `0.0`，不得作为可配置项暴露给用户（配置文件中的 temperature 字段仅为文档记录，不得影响实际调用值）。

### 约束 C-04：接口签名不得偏离 ISD
函数签名、参数名、返回类型、异常类型必须严格按照 `docs/PSTDS_4_ISD_v1.md`（或同名 .docx）。不接受「更优雅的替代设计」，一致性高于局部最优。

### 约束 C-05：Phase 顺序不可跳跃
必须按 Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 顺序推进。每个 Phase 的完成门槛测试**全部绿色通过后**，才能开始下一个 Phase。

### 约束 C-06：原始数据只追加不修改
`data/raw/` 目录下的 Parquet 和 JSON 文件，一旦写入不得覆盖，只能追加。这保证回测数据的不可篡改性。

---

## 📋 工作模式说明

### 自主执行模式（推荐）
当用户说「执行 Phase X」时，按以下循环自动完成：
```
1. 读取 docs/phases/phase-X.md 中的任务列表
2. 逐个实现每个任务
3. 实现完成后立即运行对应的验证命令
4. 如果测试失败：分析原因 → 修复 → 重新运行（最多 3 轮）
5. 所有验证通过后：更新 .pstds_phase.json → 向用户报告结果
6. 等待用户确认后进入下一 Phase
```

### 失败处理规则
- 测试失败 1-2 次：分析错误信息，定位根因，修复后重跑
- 测试失败 3 次：停止，向用户报告具体失败的测试用例和错误信息，请求人工介入
- **阻塞性失败**（TG-003、REG-001、REG-003）：立即停止所有工作，优先修复，修复前不得继续任何其他任务

### 代码生成规则
- 每个文件生成前，先读取 `docs/` 目录中对应的设计文档章节
- 生成的每个函数必须包含 docstring，说明其对应的设计文档章节号
- 不猜测接口，不发明新的数据结构，完全按 ISD 定义实现

---

## 🗂️ 文档索引

所有设计文档存放于 `docs/` 目录（在项目初始化时从 .docx 转换为 .md）：

| 文件名 | 用途 | 在编码中的用途 |
|--------|------|----------------|
| `PSTDS_1_FRD_v2.md` | 功能需求 | 验收标准，每个功能「做什么」|
| `PSTDS_2_SAD_v2.md` | 系统架构 | 模块划分和技术选型理由 |
| `PSTDS_3_DDD_v2.md` | 详细设计 | 目录结构、DB Schema 直接参考 |
| `PSTDS_4_ISD_v1.md` | 接口契约 | **函数签名的唯一来源，不得偏离** |
| `PSTDS_5_TSD_v1.md` | 测试规范 | **测试用例的直接依据** |

---

## 🗺️ 阶段索引（按需加载）

| Phase | 文件 | 内容摘要 |
|-------|------|----------|
| 0 | `docs/phases/phase-0.md` | 环境搭建、依赖安装、骨架目录、Fixture 数据 |
| 1 | `docs/phases/phase-1.md` | 时间隔离层（最高优先级，🔴 阻塞后续） |
| 2 | `docs/phases/phase-2.md` | 数据服务层（适配器、缓存、路由） |
| 3 | `docs/phases/phase-3.md` | 智能体引擎层（LLM工厂、辩论裁判员、集成测试） |
| 4 | `docs/phases/phase-4.md` | Web UI 与基础设施（Streamlit、MongoDB、调度器） |
| 5 | `docs/phases/phase-5.md` | 回测引擎（日历、虚拟组合、绩效计算） |
| 6 | `docs/phases/phase-6.md` | 收尾与 v1.0 发布（导出、通知、Docker、文档） |

---

## 🔄 阶段状态管理

每个 Phase 完成后，自动更新 `.pstds_phase.json`：

```python
# 在每个 Phase 门槛验证全部通过后执行
import json
from datetime import datetime

state = json.load(open(".pstds_phase.json"))
state["completed_phases"].append(state["current_phase"])
state["current_phase"] += 1
state[f"phase_{state['current_phase']-1}_completed_at"] = datetime.now().isoformat()
phase_names = {1: "时间隔离层", 2: "数据服务层", 3: "智能体引擎层", 4: "Web UI", 5: "回测引擎", 6: "收尾发布"}
state["phase_name"] = phase_names.get(state["current_phase"], "完成")
json.dump(state, open(".pstds_phase.json", "w"), indent=2, ensure_ascii=False)
print(f"✅ Phase {state['current_phase']-1} 已完成，进入 Phase {state['current_phase']}: {state['phase_name']}")
```

---

## ⚠️ 已知约束与边界

- 系统不提供实盘交易接口，不与任何券商 API 对接
- A 股数据实时性受 AKShare 免费接口限制（15-30 分钟延迟），不适用于日内交易
- Trading-R1 模型尚未开源，`pstds/llm/` 中保留占位类 `TradingR1Adapter`，待官方发布后启用
- 所有分析结果仅供参考，不构成投资建议

---

*CLAUDE.md v2.0 — PSTDS 项目配置（按需加载版）| 最后更新：2026年2月*
