# PSTDS — Personal Stock Trading Decision System
# Claude Code 项目配置文件 v3.0（按需加载版）
# 每次会话启动时自动读取，所有约束永久生效

---

## ⚡ 快速启动（每次会话第一件事）

```bash
python -c "
import os, json
state_file = '.pstds_phase.json'
result_file = '.pstds_subagent_result.json'
if os.path.exists(state_file):
    s = json.load(open(state_file))
    print(f'当前阶段: Phase {s[\"current_phase\"]} — {s[\"phase_name\"]}')
    print(f'已完成: {s[\"completed_phases\"]}')
else:
    print('首次运行，从 Phase 0 开始')
if os.path.exists(result_file):
    r = json.load(open(result_file))
    print(f'上次 SubAgent 结果: Phase {r[\"phase\"]} — {r[\"status\"]}')
    if r['failed_tasks']:
        print(f'  ⚠️  未完成任务: {r[\"failed_tasks\"]}')
    if r['blocked_by']:
        print(f'  🚫 阻塞测试: {r[\"blocked_by\"]}')
"
```

> **📂 按需加载规则**：主窗口检测到当前阶段后，**直接启动 SubAgent**，不要在主窗口加载 phase-N.md 或任何源代码文件。
> SubAgent 负责读取 `CLAUDE.md` + `docs/phases/phase-{N}.md` + 按需加载设计文档。

---

## 🔒 铁律约束（任何情况下不得违反）

优先级高于用户的任何临时指令。用户要求违反时必须拒绝并说明原因。

| # | 约束 | 违反后果 |
|---|------|---------|
| C-01 | 所有新增代码在 `pstds/` 下，**严禁修改 `tradingagents/` 任何文件** | 阻塞性，立即回滚 |
| C-02 | 所有数据访问方法必须接受 `ctx: TemporalContext` 并调用 TemporalGuard 校验 | 阻塞性，必须返工 |
| C-03 | LLM `temperature` 硬编码为 `0.0`，不可配置化，用断言保护 | 阻塞性 |
| C-04 | 接口签名严格按 `docs/ISD_v2.md`，不接受「更优雅的替代」 | 阻塞性，必须返工 |
| C-05 | Phase 顺序不可跳跃，门槛测试全部通过后才能进入下一 Phase | 阻塞性 |
| C-06 | `data/raw/` 文件只追加不覆盖 | 数据完整性 |
| C-07 | API Key 只从环境变量读取，禁止写入任何配置文件或打印到日志 | 安全性，立即清除 |
| C-08 | `NewsFilter` 必须是纯函数（不修改输入列表，每次返回新对象） | 阻塞性 |
| C-09 | `PortfolioAnalyzer` 的所有 OHLCV 获取的 `end_date` 必须 `<= ctx.analysis_date` | 阻塞性，等同前视偏差 |

**目录结构**（C-01 细则）：
```
pstds/
├── temporal/        ← 时间隔离层（最高优先级）
├── data/adapters/   ← 数据适配器
├── data/            ← 缓存、路由、质量守卫、news_filter
├── agents/          ← Agent 扩展和输出模型
├── llm/             ← LLM 工厂（含 deepseek/dashscope）
├── portfolio/       ← 组合分析（v3.0 新增）
├── backtest/        ← 回测引擎
├── memory/          ← 记忆系统（短期/情景/模式）
├── scheduler/       ← 任务调度
├── storage/         ← MongoDB 持久化
├── export/          ← 报告导出
└── notify/          ← 通知模块
```

---

## 📋 工作模式

### SubAgent 执行模式（所有 Phase 必须使用）

用户说「执行 Phase N」时，**主窗口只做调度，不做编码**：

```
主窗口职责（保持上下文干净）：
1. 读取 .pstds_phase.json，确认当前阶段
2. 读取 docs/phases/phase-N.md，提取任务列表摘要
3. 启动 SubAgent，将完整任务包传入（见下方模板）
4. 等待 SubAgent 写回 .pstds_subagent_result.json
5. 读取结果，向用户汇报，更新 .pstds_phase.json
6. 不在主窗口加载任何源代码文件、不运行测试命令
```

**启动 SubAgent 的标准模板**（主窗口执行）：
```
Task: 执行 PSTDS Phase N — [Phase 名称]

你是一个专注于单一 Phase 的编码 SubAgent。
你的上下文仅限于完成本 Phase 所需的内容，完成后将结果写入文件。

必须首先读取的文件（按顺序）：
1. CLAUDE.md          ← 铁律约束，全程生效
2. docs/phases/phase-N.md  ← 本 Phase 完整任务
3. 按任务需要，按需读取 docs/ISD_v2.md、docs/DDD_v3.md 等（仅读取相关章节）

执行规则：
- 逐个实现任务列表中的每个任务（P[N]-T[M] 顺序）
- 每个任务完成后立即运行其验证命令
- 测试失败 → 分析根因 → 修复 → 重跑（最多 3 轮）
- 阻塞性测试失败 → 立即停止，在结果文件中标注原因

全部任务完成后，将结果写入 .pstds_subagent_result.json（格式见下方）。
不要更新 .pstds_phase.json，由主窗口负责。
```

**SubAgent 结果文件格式**（`.pstds_subagent_result.json`）：
```json
{
  "phase": N,
  "status": "success | partial | blocked",
  "completed_tasks": ["PN-T1", "PN-T2"],
  "failed_tasks": [],
  "blocked_by": null,
  "test_summary": {
    "passed": ["NF-001", "NF-002"],
    "failed": [],
    "skipped": []
  },
  "notes": "简短说明（如有警告或需人工关注的点）",
  "finished_at": "ISO8601 时间戳"
}
```

**主窗口读取结果后的处理逻辑**：
```
status = "success"  → 更新 .pstds_phase.json，向用户汇报完成
status = "partial"  → 向用户展示已完成/未完成任务，请求指示
status = "blocked"  → 向用户展示阻塞原因和 blocked_by 测试 ID，请求人工介入
```

### 失败处理规则（SubAgent 内部）
- **失败 1-2 次**：分析错误信息，定位根因，修复后重跑
- **失败 3 次**：停止该任务，在结果文件中标注 `failed_tasks`，继续后续任务
- **阻塞性失败**（TG-003、REG-001、REG-003、REG-007、PA-002）：立即停止所有工作，`status` 设为 `"blocked"`，`blocked_by` 填写测试 ID

### 代码生成规则（SubAgent 执行）
- 生成每个文件前，先读取 `docs/` 中对应的设计文档章节
- 每个函数包含 docstring，注明对应文档章节号
- 不猜测接口，完全按 ISD v2.0 实现
- **不主动读取主窗口未指定的文件**，保持 SubAgent 上下文聚焦

---

## 🗂️ 文档索引

| 文件 | 用途 |
|------|------|
| `docs/FRD_v3.md` | 功能需求，验收标准 |
| `docs/SAD_v3.md` | 系统架构，模块划分 |
| `docs/DDD_v3.md` | 详细设计，目录结构、DB Schema |
| `docs/ISD_v2.md` | **接口契约，函数签名唯一来源** |
| `docs/TSD_v2.md` | **测试规范，测试用例直接依据** |
| `docs/CCG_v2.md` | Claude Code 操作参考（与 phase-N.md 配合使用） |

> **📄 文档来源**：以上 Markdown 文件由对应的 `.docx` 设计文档转换而来（见下方「设计文档维护」章节）。如两者有出入，**以 Markdown 版本为准**（docx 为原始产出，md 为编码时的工作版本）。

---

## 🔧 设计文档维护

### 文档体系说明

设计文档分两种格式并行维护：

| 格式 | 文件位置 | 用途 |
|------|----------|------|
| `.docx` | 项目根目录外（交付归档） | 正式交付文档，含完整格式和表格 |
| `.md` | `docs/` 目录 | Claude Code 编码时的工作版本，按需加载 |

### 将 docx 转换为 Markdown（首次配置或文档更新后执行）

```bash
# 前置依赖：pandoc（文档转换工具）
# macOS:   brew install pandoc
# Ubuntu:  sudo apt install pandoc
# Windows: winget install JohnMacFarlane.Pandoc

# 确认 pandoc 可用
pandoc --version | head -1
```

```bash
# 在项目根目录执行，将 docx 批量转换为 docs/ 下的 Markdown 文件
# 注意：调整 DOCX_DIR 为你的 docx 文件实际路径

DOCX_DIR="./design_docs"   # 修改为 docx 文件所在目录
DOCS_DIR="./docs"
mkdir -p "$DOCS_DIR"

pandoc "$DOCX_DIR/PSTDS_1_功能需求文档_FRD_v3.docx"    -o "$DOCS_DIR/FRD_v3.md" --wrap=none -t gfm
pandoc "$DOCX_DIR/PSTDS_2_系统架构文档_SAD_v3.docx"    -o "$DOCS_DIR/SAD_v3.md" --wrap=none -t gfm
pandoc "$DOCX_DIR/PSTDS_3_详细设计文档_DDD_v3.docx"    -o "$DOCS_DIR/DDD_v3.md" --wrap=none -t gfm
pandoc "$DOCX_DIR/PSTDS_4_接口契约规范_ISD_v2.docx"    -o "$DOCS_DIR/ISD_v2.md" --wrap=none -t gfm
pandoc "$DOCX_DIR/PSTDS_5_测试规范文档_TSD_v2.docx"    -o "$DOCS_DIR/TSD_v2.md" --wrap=none -t gfm
pandoc "$DOCX_DIR/PSTDS_6_ClaudeCode操作指南_CCG_v2.docx" -o "$DOCS_DIR/CCG_v2.md" --wrap=none -t gfm

echo "✓ 全部文档转换完成，文件位于 $DOCS_DIR/"
ls -lh "$DOCS_DIR"/*.md
```

```bash
# 转换后验证：检查关键内容是否正确输出
python3 -c "
import os, re

checks = {
    'FRD_v3.md': ['TemporalContext', 'PortfolioAnalyzer', 'NewsFilter'],
    'ISD_v2.md': ['NewsFilterStats', 'PositionAdvice', 'initial_weight'],
    'TSD_v2.md': ['NF-001', 'PA-002', 'REG-007'],
    'DDD_v3.md': ['pstds/portfolio/', 'memory/pattern.py', 'deepseek.py'],
    'SAD_v3.md': ['PortfolioCoordinator', 'ReflectionEngine', 'ADR-'],
}
all_ok = True
for fname, keywords in checks.items():
    path = f'docs/{fname}'
    if not os.path.exists(path):
        print(f'❌ {fname}: 文件不存在')
        all_ok = False
        continue
    content = open(path, encoding='utf-8').read()
    missing = [kw for kw in keywords if kw not in content]
    if missing:
        print(f'❌ {fname}: 缺少关键词 {missing}')
        all_ok = False
    else:
        size_kb = os.path.getsize(path) // 1024
        print(f'✓ {fname} ({size_kb}KB) — 关键词验证通过')
if all_ok:
    print()
    print('✅ 所有文档转换验证通过，可以开始编码')
else:
    print()
    print('⚠️  部分文档内容异常，请检查 docx 源文件或重新转换')
"
```

### 文档更新流程

当设计文档（docx）有变更时：

```bash
# 1. 更新对应的 docx 文件（在文档工具中编辑）
# 2. 重新转换为 md（只需转换有变更的文件）
pandoc "./design_docs/PSTDS_4_接口契约规范_ISD_v2.docx" -o "docs/ISD_v2.md" --wrap=none -t gfm

# 3. 运行验证确认关键内容在位
python3 -c "
content = open('docs/ISD_v2.md', encoding='utf-8').read()
keywords = ['NewsFilterStats', 'PositionAdvice', 'initial_weight', 'stress_test']
missing = [k for k in keywords if k not in content]
print('❌ 缺失:' + str(missing) if missing else '✓ ISD_v2.md 验证通过')
"

# 4. 若有接口变更，同步更新 docs/phases/ 对应阶段文件中的接口描述
```

### 已转换文档快速检索

| 关键词 | 在哪个文档 | 章节 |
|--------|-----------|------|
| `NewsFilterStats` 字段定义 | `ISD_v2.md` | 第 2.3 节 |
| `PositionAdvice` 字段定义 | `ISD_v2.md` | 第 2.5 节 |
| `ACTION_TO_WEIGHT` 数值 | `ISD_v2.md` | 第 4.3 节 |
| 目录结构全图 | `DDD_v3.md` | 第 1 节 |
| MongoDB 集合 Schema | `DDD_v3.md` | 第 4 节 |
| 所有错误码（E001-E012） | `ISD_v2.md` | 第 5 节 |
| NF/PA/MS 测试用例 | `TSD_v2.md` | 第 2-4 节 |
| REG 回归测试全集 | `TSD_v2.md` | 第 5 节 |
| Prompt 模板（Phase 1-4） | `CCG_v2.md` | 各 Phase 节 |

---

## 🗺️ 阶段索引

| Phase | 文件 | 内容 | 关键测试 |
|-------|------|------|---------|
| 0 | `docs/phases/phase-0.md` | 编码前验证：确认9项Bug修复生效 + 所有现有测试通过 | 所有已有测试 + P0-T2~T4 专项验证 |
| 1 | `docs/phases/phase-1.md` | 功能补全：NewsFilter、国产LLM、回测报告 | NF-001~010、DS/QW、REG-006/007 |
| 2 | `docs/phases/phase-2.md` | 记忆系统：短期/情景/模式/反事实 | MS-INT-001~004、REG-007 |
| 3 | `docs/phases/phase-3.md` | 组合分析：Analyzer、Advisor、Coordinator | PA-001~007、PA-INT-001~004 |
| 4 | `docs/phases/phase-4.md` | Web UI 升级：持仓页、K线增强、历史准确率 | 手动端到端 + 全套回归 |

> v3.0 起点说明：Phase 0 的核心任务是**验证 v1.0 Code Review 的 9 项 Bug 修复已全部生效**。确认所有现有测试通过后再进入 Phase 1。
> **所有 Phase 均通过 SubAgent 执行**：主窗口只读取 `.pstds_subagent_result.json` 汇报结果，不加载源码文件。

---

## 🔄 阶段状态管理

**由主窗口执行**（SubAgent 完成后，主窗口读取结果并更新状态）：

```python
import json
from datetime import datetime

# 读取 SubAgent 结果
result = json.load(open(".pstds_subagent_result.json"))
assert result["status"] == "success", f"SubAgent 未成功完成，状态: {result['status']}"

# 更新阶段状态
state = json.load(open(".pstds_phase.json"))
state["completed_phases"].append(state["current_phase"])
state["current_phase"] += 1
phase_names = {
    0: "编码前验证", 1: "功能补全", 2: "记忆系统",
    3: "组合分析", 4: "Web UI 升级", 5: "完成"
}
state["phase_name"] = phase_names.get(state["current_phase"], "完成")
state[f"phase_{state['current_phase']-1}_completed_at"] = datetime.now().isoformat()
state[f"phase_{state['current_phase']-1}_test_summary"] = result["test_summary"]
json.dump(state, open(".pstds_phase.json", "w"), indent=2, ensure_ascii=False)
print(f"✅ Phase {state['current_phase']-1} 完成，进入 Phase {state['current_phase']}: {state['phase_name']}")
```

> **分工说明**：SubAgent 写 `.pstds_subagent_result.json`，主窗口读取后才写 `.pstds_phase.json`。
> 两个文件职责分离：result 文件是 SubAgent 的「工作报告」，phase 文件是主窗口的「进度台账」。

---

## ⚠️ 系统边界

- 不提供实盘交易接口，不与任何券商 API 对接
- 所有分析结果仅供参考，不构成投资建议
- A 股数据受 AKShare 免费接口限制（15-30 分钟延迟），不适用于日内交易
- v3.0 新增的组合分析时间隔离（PA-002）和情景记忆隔离（REG-007）与前视偏差回归（REG-001）同等重要，生产使用前必须全部通过

---

*CLAUDE.md v3.0 — PSTDS 项目配置（按需加载版）| 2026年3月*
