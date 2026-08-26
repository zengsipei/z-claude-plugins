# dsh-spec v2 · 强类型/防御式门禁设计（PROTOTYPE — D-v2-4 #30）

> PROTOTYPE，非交付物。用于反应取舍。真实 SKILL.md 落地归 #32（命令/技能面与命名）派生的 build 票，本文件只定「强类型/防御式门禁」的设计与信号集。
> 锁定后：结论写入 #30 的 resolution comment 并关闭；本文件保留为设计史（build 票可并入或参考）。

## 背景约束（已锁定，无需重议）

- R-v2-3 (#26)：强类型门禁**仅当检测到对应工具链时启用，否则静默跳过**；不得因缺 TS 报错或强装包。形态 = warn-only rot 检查（默认）+ 可选 strict review 轴（人触发），**任何形态都不许 PreToolUse 硬阻断**；CI 硬门禁违反 R2（#23 Out of scope）。
- D-v2-1 (#27)：v2 收口 = 三大支柱设计 + 分工澄清；**支柱3 强类型 = rot warn-only + 可选 `--axis types`**；多项目/monorepo 顺延 Out of scope。
- D-v2-2 (#28)：test 轴 = review 轴 `--axis test`（人触发、`--gate strict` 非零退出、不 PreToolUse）；`--gate` 对所有选中轴统一生效。
- D-v2-3 (#29)：simplify = rot 第五查 `--check simplify`（warn-only、报告-only、两层信号、零自动修）。
- v1 `dsh-spec-rot`：`--check <all|docs|notes|tests|adr>`，默认 `all`；输出「按严重度排序的清单，含文件与具体漂移点」；`tests` 查「有则跑、记录退化、无则跳过」。本票沿用该形态。

## 决策摘要（设计建议，待 reaction）

强类型/防御式门禁以**双形**并入：默认 `dsh-spec-rot --check types`（warn-only、随 v1 Stop 钩子 rot 运行、零退出）作日常提醒；可选 `dsh-spec-review --axis types`（人触发、合并前、`--gate strict` 缺口即非零退出、不 PreToolUse）作合并把关。两类均先做**工具链探测**——首选复用消费项目既有 linter（零新增依赖），TS 风味无显式配置按 `tsc --strict` → Biome → ESLint 启发式回退，无工具链则跳过。信号分自包含层（grep 类型退化气味，仅 TS/JS 仓）与工具增强层（类型严格度错误数，有工具才跑）。

---

## 1. 形态：rot warn-only（默认）+ review 轴（可选）（Q1）

与 #27 一致，双形而非二选一：

- **默认 — rot warn-only**：`dsh-spec-rot --check types`（warn-only、报告-only、零退出）。并入 v1 rot 的检查枚举：
  - `--check <all|docs|notes|tests|adr|simplify|types>`，默认 `all`（含 types）。
  - 随 v1 既有 Stop 钩子 rot 运行（见 §4），不改钩子语义。
- **可选 — review 轴 `--axis types`**：`dsh-spec-review --axis types`（人触发、合并前、复用 `--gate strict|warn`）。
  - 复用 #28 已预留的 `--axis` 机制（`--axis <all|code|spec|notes|test|types>`），与 test 轴同级接口位。
  - `--gate strict`：类型退化即非零退出，阻断合并**决定**（人仍拍板）；`--gate warn`：仅报告。
  - **不** PreToolUse 硬阻断（R2 #18 硬约束）。

> 不在 build 层（PreToolUse）做任何拦截；CI 硬门禁属 #23 Out of scope。

## 2. 工具链探测与回退（Q2）

两形共用同一探测逻辑，复用 R-v2-3 结论：

1. **首选复用消费项目既有 linter**（零新增依赖）：检测仓库已有的 `tsconfig`（strict）、`biome.json`、`eslint` 配置、或 `package.json` 的 `lint` 脚本，优先直接调用。
2. **TS 风味但无显式配置**：按 `tsc --strict --noEmit` → Biome `check` → ESLint（类型感知）**启发式回退**，取首个可用。
3. **无工具链**：静默跳过，标注「无类型工具链，跳过」，**绝不报错、绝不强装包**（类比 v1 `tests` 查「无测试，跳过」）。
4. 非 TS/JS 仓（如纯 Python/Go）：自包含层信号不适用，标注「非 TS/JS，跳过」；工具增强层不跑。

> 探测结果对 rot 与 review 轴一致，避免同一仓两种结论。

## 3. 信号与报告（Q3）

沿用 v1 rot 发现清单：`{文件, 信号, 度量值, 建议}`，按严重度（高→低）排序，零自动修。

### 自包含层（零依赖恒可跑，仅 TS/JS 仓）
纯 grep，无需工具链：
- 显式 `any` 计数（含 `as any`、`as unknown as`）。
- 非空断言 `!` 计数（`obj!.prop`）。
- 类型压制注释 `@ts-ignore` / `@ts-expect-error` 计数。
- 类型断言 `as` 计数（强转气味）。
> 阈值可配（rot 配置块 / `--types-thresholds`），有默认值、零配置可跑。

### 工具增强层（有工具链才跑，无则跳过）
- `tsc --strict --noEmit` 错误数；或
- Biome 类型相关规则错误数；或
- ESLint 类型感知规则错误数（取 §2 探测到的那个）。
> 输出具体文件与错误点（沿用 v1「含文件与具体漂移点」）。

### 不纳入（明确 Out of scope）
- **运行时不变量**（R-v2-1 的 dsh CI 硬门禁）：过重、需运行态，warn-only 不跑；本票「防御式」仅指**类型层防御性信号**（即上述 any/断言气味），不扩展到运行态断言。
- 自动重构（rot 只报告）。
- 覆盖率 / 快照（属 test 轴，D-v2-2）。

## 4. Stop 钩子接入（Q4）

- `types` 检查作为 rot `--check types`（默认含于 `--check all`），**随 v1 既有 Stop 钩子 rot 运行**。
- 形态不变：warn-only、零退出、仅报告 → **不改钩子语义**（仍是「提醒而非阻断」）。
- 这同时部分解答地图 Not yet specified 的「Stop 钩子接入」问题：**新增检查沿用 v1 rot 通道，零退出、不引入 PreToolUse，钩子语义不变**。

## 5. 与 test 轴 / simplify 查 / 其他支柱的边界（Q5）

- **rot `--check types`（默认 warn-only）↔ review `--axis types`（可选 strict）**：日常提醒 vs 合并前把关，正交，类比 test 轴 ↔ rot `tests`。
- **types（类型严格度）↔ simplify（规模/重复）↔ test（测试不变量）**：三者维度互不重叠，均可在 rot 并存、`--check all` 一并产出。
- **分工**：rot 管「类型是否退化」（运行态/日常），review 轴管「新改动是否引入类型退化」（设计态/合并前）。
- **不碰 build 层**（R2 硬禁）；CI 硬门禁 Out of scope（#23）。

## 6. 命令/技能面与命名（Q6）

- 真实 SKILL.md 落地（参数枚举扩展 `--check types` + `--axis types`、工具链探测、阈值配置、输出格式、跳过分支）归 #32 派生 build 票。
- 命名沿用 v1 约定：rot 查名 `types`、review 轴名 `types`；**不引入新概念名**（符合地图 Notes 命名约定）。

---

## 已锁定取舍（D-v2-4 设计结论推荐 — Q1–Q6，待用户 reaction）

- **Q1**：双形——默认 `dsh-spec-rot --check types`（warn-only）+ 可选 `dsh-spec-review --axis types`（人触发、`--gate strict` 非零退出、不 PreToolUse）。
- **Q2**：工具链探测首选复用消费项目既有 linter；TS 风味无配置按 `tsc --strict` → Biome → ESLint 回退；无工具链静默跳过、不装包。
- **Q3**：信号分两层——自包含层（grep `any`/非空断言/`@ts-ignore`/`as` 计数，仅 TS/JS）+ 工具增强层（类型严格度错误数，有工具才跑）；输出 v1 rot 清单、按严重度排序、零自动修；运行时不变量 Out of scope。
- **Q4**：`types` 检查随 v1 既有 Stop 钩子 rot 运行，warn-only、零退出、不改钩子语义。
- **Q5**：rot `types` ↔ review `--axis types` 正交（类比 test 轴 ↔ rot tests）；与 simplify/test 维度互不重叠；不碰 build 层。
- **Q6**：真实落地归 #32 派生 build 票；命名沿用 `types`，不引入新概念。

## 状态
- D-v2-4 (#30) 原型已起；结论按 Q1–Q6 推荐待用户 reaction 锁定，由 #30 resolution 记录并关闭。
- 真实落地归 #32（命令/技能面与命名）派生 build 票；本文件保留为设计史。
