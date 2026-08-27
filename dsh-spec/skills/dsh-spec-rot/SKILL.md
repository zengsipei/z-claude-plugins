---
name: dsh-spec-rot
description: 漂移与一致性巡检——六查：docs（文档漂移）、notes（无 note 的 commit）、tests（测试退化）、adr（ADR 过期）、simplify（复杂度增长）、types（类型退化）。当用户说「巡检」「漂移检查」「rot 检查」，或按时/随 Stop 钩子触发时调用。恒 warn-only、零退出、只报告不自动修复。
---

# dsh-spec-rot

及早暴露腐烂，便于低成本修复。只报告，不自动修复。本技能恒受 `.agents/RULES.md` §8 warn-only 宪法约束（恒零退出、绝不 PreToolUse、跳过是一等非致命结果）；随 v1 既有 Stop 钩子（`hooks/dsh-spec-gate.py`）例行运行时钩子语义不变。

## 参数

- `--check <all|docs|notes|tests|adr|simplify|types>`：默认 `all`（六查全跑）。可多选（逗号分隔，如 `--check docs,simplify`）。枚举之外的任何值（含组合中的非法元素）→ 报参数错误退出——这是唯一的报错退出路径（§8）；任何检查发现本身恒零退出。
- `--simplify-thresholds <k=v,…>`：simplify 查阈值局部覆盖（只覆盖给出的键，其余用默认）。默认值见 `.agents/RULES.md` §6（loc-warn / loc-high / exports）。
- `--types-thresholds <k=v,…>`：types 查阈值局部覆盖。默认值见 §6（any / non-null / ts-suppression / as-assert；语义：每文件计数**超过**阈值即一条 warn 发现）。

## 步骤

1. 解析 `--check`（默认 all），展开为检查集合（执行顺序固定：docs → notes → tests → adr → simplify → types）。
   - 完成判定：检查集合已确定；非法 `--check` 值已报错退出。
2. 对每个选中的检查产出发现。发现 = `{文件, 信号, 度量值, 建议}`；**跳过是一等非致命结果**（输出跳过标注，沿用 v1 `tests`「无测试，跳过」形态，绝不报错、绝不装包）：
   - `docs` / `notes` / `tests` / `adr`：v1 四查，行为不变（定义见下节）。
   - `simplify`：见「查·simplify」。
   - `types`：见「查·types」。
   - 完成判定：每个选中检查要么有发现列表、要么有跳过标注、要么标 ok。
3. 输出按严重度（高→低）排序的清单，含文件与具体漂移点；对满足 `.agents/RULES.md` §9 候选条件的 note 给出「建议归档」提示（归档协议整体见 §9：人工确认后执行，rot 只建议不动手）。
   - 完成判定：用户拿到可处理的腐烂报告。**发现再多也零退出**。

## v1 四查（行为不变）

- `docs`：`ARCHITECTURE.md` 声明的模块/不变量/契约与实际代码结构（文件、导出、依赖）漂移。
- `notes`：自上次 note（`.agents/LEDGER.md` 最新日期）起的 `git log` commit 无对应 `.agents/notes` 条目。
- `tests`：若项目存在测试套件则运行，记录退化（失败/跳过增多）；无测试则标注「无测试，跳过」。
- `adr`：ADR 被推翻但未标 `superseded-by`/`rejected`，或其关联代码已不符。

## 查·simplify —— 简化发现（复杂度增长信号）

与 docs 查正交：docs 查「声明 vs 实际」结构一致性，simplify 查「规模/重复」增长信号。分两层，零配置即可跑自包含层。

### 自包含层（零依赖，恒可跑 —— 纯 git / grep / LOC）

- **模块体积**：`*.ts` / `*.js` / `*.py`（含 `.tsx`/`.jsx`/`.mjs`/`.cjs` 变体）单文件物理 LOC（`wc -l`）：> `loc-warn` → warn；> `loc-high` → 高（默认值见 `.agents/RULES.md` §6）。建议：按职责拆为多个模块。
- **单文件导出数**：`export` 出现次数 > `exports`（默认值见 §6）→ warn。建议：聚合同类导出或拆为子模块。

### 工具增强层（消费项目本地有该工具才跑；缺席输出「未配置 <tool>，跳过」，绝不报错、绝不装包）

- **重复片段**：`jscpd`（若本地存在；沿用默认 `minLines 6` / `minTokens 60`）。发现：重复处数与行数 → 建议抽公共函数。
- **死代码/未用导出**：`knip`（若消费项目已配置）。发现：未用导出/死文件 → 建议删除或收敛导出面。
- **圈复杂度**：`sonarjs` / eslint `complexity` 规则（若消费项目已配置）。发现：高复杂度函数 → 建议抽函数。

报告-only、零自动修：「建议」是人工执行提示，修复走正常改动 + `/dsh-spec-note`。

## 查·types —— 类型退化（warn-only 日常提醒）

与 `/dsh-spec-review --axis types`（合并前把关、可 strict）正交：rot 管全仓运行态/日常退化，review 轴管新改动设计态。仅 TS/JS 仓适用；非 TS/JS 仓标注「非 TS/JS，跳过」、本查零发现。

### 工具链探测

按 `.agents/RULES.md` §7 执行；与 `/dsh-spec-review --axis types` 共用同一 §7 链，同一仓结论一致。

### 自包含层（零依赖恒可跑）：全仓 TS/JS 文件逐文件按 §7 气味清单 grep 计数

每文件计数**超过**对应阈值即一条 warn 发现（阈值默认值见 §6，`--types-thresholds` 可局部覆盖）。建议：给概念一个真实类型 / 收敛断言。

### 工具增强层（有工具链才跑）

运行探测到的工具，取类型严格度错误，报告具体文件与错误点。warn-only：工具错误也只是发现，零退出。

## 范围

只检测与建议，恒受 `.agents/RULES.md` §8 宪法约束（warn-only、零退出；唯一报错退出 = `--check` 非法枚举）。修复走正常改动 + `/dsh-spec-note`。类型退化的合并前把关走 `/dsh-spec-review --axis types`；新改动的测试不变量走 `--axis test`；rot `tests` 查保持 v1 形态不升级。simplify/types 随 v1 既有 Stop 钩子 rot 通道运行（钩子语义不变）。不纳入快照/覆盖率/模块图/字数预算/运行时不变量/自动重构（v2 锁定 Out of scope）。
