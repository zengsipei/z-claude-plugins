# RULES — dsh-spec 共享规则（单一事实源）

> **本文件是全部共享规则的唯一权威持有处。**任何其它文件（CLAUDE.md、README、commands、skills、hook 代码）只引用本文件的 `§` 锚点，不复制规则文本——改规则只改这里，其余文件随引用自动生效。
>
> `/dsh-spec-init` 会把本文件复制到消费项目 `.agents/RULES.md`；skill 执行时以「消费项目内的那份」为准读数。

## §1 分类法（六类）

`feature` / `bug-fix` / `simplification` / `architecture` / `process` / `testing`

note 与 LEDGER 的 `<class>` 维度取值即这六个，不加第七类；新类别先改这里。note 命令 `--class` 默认 `feature`。

## §2 lifecycle（三态）

`proposed` / `implemented` / `rejected`

- note 路径第一层与 frontmatter `Status:` 用此三态。
- `--lifecycle` 默认 `implemented`；计划阶段用 `proposed`。
- 归档只对 `implemented` 开放，删除见 §9。

## §3 slug 约束

kebab-case、纯 ASCII 小写、≤40 字符、禁中文/大写。例：`add-retry-backoff`。

不合格 slug → 提示重命名，不静默修正。

## §4 note 路径模式

```
.agents/notes/<lifecycle>/<class>/<date>-<slug>.md
```

lifecycle 在外、class 在内。归档例外见 §9。

## §5 note 模板（完整，单一事实源）

```markdown
---
Status: <proposed|implemented|rejected>   ← 取值即 §2 三态
---

## Problem
<改动缘起>                                 ← 恒必填

## Decision
<改动本身（implemented / rejected 用此节）>

## Proposal
<改动方案（proposed 用此节）>               ← Decision / Proposal 按 lifecycle 二选一，恒必填

## Alternatives considered
- <备选 A>：<为何不选>                      ← 恒必填（哪怕只列「什么都不做」）

## Consequences
<收益或代价>                                ← proposed/implemented 必填；rejected 可空
```

frontmatter 除 `Status:` 外唯一允许的其它字段是 `Archived:`（§9.1 归档协议）。

## §6 阈值默认值

两套口径互相独立：

- **review types 轴**（diff 计数，窗口 = `--since` 起）：对新增行的气味计数即缺口本身，无数值阈值——新引入的类型退化一条也是缺口。
- **rot types 查**（全仓计数）：每文件计数**超过**阈值即一条 warn 发现。默认 `any=3`、`non-null=3`、`ts-suppression=0`、`as-assert=5`。
- **rot simplify 查**：单文件 LOC > `loc-warn`(400) → warn；> `loc-high`(800) → 高；单文件 `export` 计数 > `exports`(20) → warn。

阈值可经对应命令的局部覆盖参数临时压过，不回写本文件。

## §7 types 工具链探测链 + 气味清单

**探测链**（review types 轴与 rot types 查共用同一链、同一仓结论一致）：

1. 首选复用消费项目既有 linter（零新增依赖）：按序检测 `tsconfig.json`（strict）→ `biome.json` → eslint 配置（`eslint.config.*`/`.eslintrc*`）→ `package.json` 的 `lint` 脚本，命中即直接调用。
2. TS 风味但无显式配置：回退链 `tsc --strict --noEmit` → `biome check` → `eslint`，取首个**本地已可用**者。
3. 全无 → 标注「无类型工具链，跳过」（跳过的只是工具增强层；自包含层照跑）。

恒定铁律：只探测、**绝不装包**。

**气味清单**（自包含层 grep 计数的四类）：

1. 显式 `any`（含 `as any`、`as unknown as`）
2. 非空断言 `obj!.prop`、`foo!`
3. `@ts-ignore` / `@ts-expect-error`
4. `as` 类型断言（强转气味）

## §8 warn-only 宪法条款（单一锚点）

凡带「巡检/提醒」性质的检查（rot 六查、Stop 钩子），遵守以下宪法：

- **恒 warn-only**：发现永远是提醒，不是阻断。
- **恒零退出**：退出码一律 0；唯一例外是参数枚举非法（如 rot `--check` 收到枚举之外的值）报错退出。
- **绝不 PreToolUse**：任何形态都不做工具调用前的硬阻断；硬阻断只属于人触发的 `/dsh-spec-review --gate strict`（权威闸口）。
- **只报告不修复**：「建议」是给人的人工执行提示，修复走正常改动 + `/dsh-spec-note`。
- **跳过是一等非致命结果**：无测试、「未配置 `<tool>`」、「非 TS/JS」、「无类型工具链」都输出标注后继续，绝不报错、绝不装包。

新增任何检查轴/查，自动受本节约束；实现文件不得另行放宽或加严。

## §9 归档与删除协议

note 退出现役只有两条路：**9.1 归档**（保留历史价值）或 **9.2 删除**（不值得留）。二选一，不得并存。

### 9.1 归档

已落地且无后续动作、但**仍具历史决策价值**的 note 归档规则：

1. **标记**：note frontmatter 加一行 `Archived: <YYYY-MM-DD>`（与 `Status:` 并列，唯一其它允许字段）。
2. **迁移**：整个 note 文件迁入 `.agents/notes/archived/<class>/<date>-<slug>.md`——lifecycle 层被 `archived/` 取代，class 保留。**只有 `implemented` 可归档**（`archived/` 有意不设 lifecycle 层）；过时的 `proposed` 先转 `rejected`，**永不归档 proposed**。
3. **索引更新**：`.agents/LEDGER.md` 对应行**原地更新**为 `- [<date>] <slug> — <一句话摘要> · <lifecycle> · archived`，链接指向新路径；不删行、不改排序。
4. **触发**：由 `/dsh-spec-rot` 对满足条件的 note 给出「建议归档」提示，**人工确认后执行**；`/dsh-spec-note` 与 review 不主动归档。
5. **归档时只允许上述改动**：既有标题标点、空行布局、语言切换栏措辞均不阻止归档，与正文一并保留。

候选条件（rot 判断用）：Status 为 `implemented` 且 LEDGER 日期早于最近一次同类改动。

以下情形**不**归档，继续作为活跃记录：备选方案、归属边界、否定性保证、持久化/协议语义、安全规则，或重新引入条件仍有价值。

### 9.2 删除

仅描述**小型 UI 调整或纯机械变更**的 implemented note 直接删除，不走 9.1：

1. **删除**：整份 note 文件删除，并从 `.agents/LEDGER.md` 移除对应行、修复或移除全部入站链接。
2. **排除**：局部 bug 修复、性能变更、新能力、实质行为决策**不因规模小而删除**——它们走 9.1。
3. **`rejected`**：仅当其决策依据已不能避免一种可能发生的错误时保留；否则一并删除。
4. **触发**：同 9.1 第 4 条，由 rot 提示、人工确认。

**判据不许退化为字数、存续时长或配额**——量小不等于可删，要问的是「这条记录还在防一个什么错」。

## §10 rot 六查枚举

`docs` / `notes` / `tests` / `adr` / `simplify` / `types`

rot `--check` 取值即这六个加 `all`（默认，六查全跑）；固定执行顺序 docs → notes → tests → adr → simplify → types。新查先改这里。

## §11 review 四轴枚举

`code` / `notes` / `test` / `types`

review `--axis` 取值即这四个加 `all`（默认，= 四轴全跑）；固定执行顺序 code → notes → test → types。新轴先改这里。

## §12 留账门槛（何时必须写 note）

判据一句话：**只有代码、测试和现有文档都讲不清、且具长期价值的决策理由，才必须留账。**

- **要留账**：改动引出了读不出来的「为什么」——权衡、备选方案落选的理由、被主动放弃的选项、边界划在哪。
- **可豁免**：机械性或局部编辑，包括局部 UI 展示与交互调整、改名与移动、重排。
- **判不准时**问一句：半年后有人拿到这段 diff，只读代码和测试能不能明白当初为什么这么做？能 → 不留账；不能 → 留账。

`/dsh-spec-review` 的 `notes` 轴与 `/dsh-spec-rot` 的 `notes` 查一律以此节判缺口。**「非平凡改动」不再是判据**——那个词没有定义，历史上被各处当黑箱用，导致闸门持续误报；判据只此一处。

已把一条决策写进 note 后，同主题的后续改动**更新那一条**即可，不新建重复记录。

## §13 test 轴审计范围判据（与 §12 独立，不互推）

本轴只回答一件事：**新增的可执行代码有没有被测试约束住。**它与 §12 是两把独立的尺子——局部 UI 调整可以完全不必留账，但若动了公开接口仍须有测试；反过来，测试写得再全也补不上缺失的 note。

**受审对象**：审计窗口内改动的**可执行源码**——脚本、hooks、`*.ts`/`*.js`/`*.py` 等。

**免审对象**（本轴直接通过，不要求测试）：

- 测试文件自身：`*.test.*`、`*.spec.*`、`tests/`、`test/`、`__tests__/`、`conftest.py`
- 纯文本：`*.md`、skill 文本、spec、docs
- 构建产物与锁文件

窗口内受审对象为空（如文档-only 改动）→ 本轴直接通过，**不要求测试**。

「好测试」定义、判定清单与反模式表留在 `skills/dsh-spec-review/SKILL.md`——本节只定范围，不复述判定标准。

---

## 附：脚手架清单

`/dsh-spec-init` 在消费项目生成的结构：

- `SPEC.md`
- `ARCHITECTURE.md`
- `docs/adr/`
- `.agents/notes/`
- `.agents/LEDGER.md`
- `.agents/RULES.md`（本文件在消费项目内的副本）

`hooks/dsh-spec-gate.py` 两组常量以下面两行声明为唯一事实源（由 `hooks/test_dsh_spec_gate.py` 一致性测试执法）：

- gate 采纳标记（`ADOPT_MARKERS`）：`.agents/notes` / `.agents/RULES.md` / `.agents/LEDGER.md`
- 留账路径（`NOTE_PREFIXES`）：`.agents/notes/` / `docs/adr/`

**`docs/adr/` 是留账路径，但不是采纳标记**：只建了 `docs/adr/`、没建 `.agents/` 的仓库，即使写了 ADR 也**不会**收到「本轮有未留账改动」的提醒。这是有意的——`docs/adr/` 太普遍，把它算作采纳会打扰大量与 dsh-spec 无关的仓库。想要提醒，先 `/dsh-spec-init` 建齐 `.agents/` 三件套。
