# dsh-spec v2 · 命令/技能面与命名 consolidated surface（PROTOTYPE — #32）

> PROTOTYPE，非交付物。用于反应取舍。#32 是 v2 地图的收口票：把 #28/#29/#30/#33 已锁定的三大支柱能力收束为**统一的命令/技能面与命名**，并孵化落地 build 票。
> 锁定后：结论写入 #32 resolution 并关闭；真实 SKILL.md 改写归 B1/B2/B3 build 票。本文件保留为设计史。

## 1. 命令面（数量不变：4 命令）

| 命令 | 作用 | 背后 skill | v2 变更 |
| --- | --- | --- | --- |
| `/dsh-spec-init [--root .] [--force]` | 脚手架化活文档 + 台账 | `dsh-spec-init` | 无 |
| `/dsh-spec-note "<slug>" [--class ...] [--lifecycle ...]` | 记一笔变更台账 | `dsh-spec-note` | 无 |
| `/dsh-spec-review [--since <ref>] [--gate strict\|warn] [--axis <...>]` | 合并前闸门 | `dsh-spec-review` | **新增 `--axis`** |
| `/dsh-spec-rot [--check <...>]` | 漂移巡检 | `dsh-spec-rot` | **`--check` 枚举扩展** |

结论：**不新增命令**（#27/#29 已定）。v2 只在既有 `review`/`rot` 上增量 flag。

## 2. 技能面（1:1，数量不变：4 skill）

`commands/<name>.md` 薄包装 → `skills/<name>/SKILL.md` 真逻辑。v2 不新增 skill、不引入新概念名。

## 3. `/dsh-spec-review` 参数面（v2）

- `--since <ref>`：不变（默认上次 merge-base）。
- `--gate <strict|warn>`：不变（默认 `strict`）。
- `--axis <all|code|notes|test|types>`：**新增**，显式选择评审轴，默认 `all`。
  - `code` → 委派 `code-review` skill（Standards+Spec 两轴内部不变）。[v1 行为]
  - `notes` → note/ADR 审计（逐改动匹配 `.agents/notes` 或 `docs/adr`）。[v1 行为]
  - `test` → **新增**（#28）：seam 测试审计；**内化 tdd「好测试」定义**（seam 概念 + 三类反模式：实现耦合 / 同义反复 / 水平切片）进本 rulebook，运行时零外部 `tdd` 技能依赖；自实现审计逻辑；不跑套件、不强制覆盖率、不比快照；`--gate strict` 缺口即非零退出、不 PreToolUse。
  - `types` → **新增**（#30）：类型退化审计；自包含层 grep `any`/非空断言/`@ts-ignore`/`as` 计数（仅 TS/JS）+ 工具增强层（复用消费项目 linter：`tsc --strict` → Biome → ESLint 回退，有工具才跑）；无工具链静默跳过、不装包。
  - `all`（默认）= `code,notes,test,types`。
  - 向后兼容：v1 行为 = `code,notes`；未就绪团队用 `--axis code,notes` 退出 test/types。
- 命名：`--axis` 沿用 v1 预留位（v1 SKILL.md 已注释 `--axis test` 接口位）；`test`/`types` 即能力名，不引入新概念。

### 3.1 命名取舍：弃用 `spec` 轴（#28 草稿残影修正）

#28 原型 §1 枚举曾写 `--axis <all|code|spec|notes|test>`，但 `spec` 在票内**无独立行为定义**，且其语义（code-review 的 Spec 轴）已被 `code`（委派 code-review，Standards+Spec 内部全跑）覆盖。为避免冗余/歧义轴、遵守「不引入新概念名」，#32 裁定：**去除 `spec` 轴**，`--axis` 终态枚举 = `code|notes|test|types`（+`all`）。`code` 仍 = 完整 code-review 委派。

## 4. `/dsh-spec-rot` 参数面（v2）

- `--check <all|docs|notes|tests|adr|simplify|types>`：枚举扩展，默认 `all`。
  - `docs` / `notes` / `tests` / `adr`：[v1 不变]
  - `simplify` → **新增**（#29）：简化发现；自包含层（模块 LOC>400 warn / 800 高、单文件导出>20）+ 工具增强层（jscpd 重复 / knip 死代码 / sonarjs 圈复杂度，有工具才跑、无则跳过）；输出 `{文件, 信号, 度量值, 建议}`、按严重度排序、零自动修。
  - `types` → **新增**（#30）：类型退化；自包含层（grep `any`/非空断言/`@ts-ignore`/`as` 计数，仅 TS/JS）+ 工具增强层（类型严格度错误数，有工具才跑）；阈值可配、零配置可跑自包含层；无工具链跳过。
  - `all`（默认）= 六查全跑。
  - 阈值可配：`--simplify-thresholds` / `--types-thresholds`（有默认值）。
  - 工具探测失败/缺失：标注「未配置 <tool>，跳过」「非 TS/JS，跳过」「无类型工具链，跳过」，类比 v1 `tests` 跳过分支，**绝不报错 / 强装包**。

## 5. Stop 钩子（不变）

- `hooks/dsh-spec-gate.py`（warn-only 提醒闸口）**语义不变**。
- v2 新增的 `simplify`/`types` 检查**复用既有 rot Stop 通道**（warn-only、零退出），不新增钩子、不改钩子语义（#29/#30 已定）。部分解答地图 Not yet specified「Stop 钩子接入」：新增检查一律走 v1 rot 通道，零退出、不 PreToolUse。

## 6. 命名铁律（v2 锁定）

- 插件名 `dsh-spec`（不变）；命令与技能同名（不变）。
- 不引入新概念名：新轴 / 新查以能力命名 —— `test` / `types` / `simplify`。
- flag 名沿用 v1：`--since` / `--gate` / `--axis` / `--check`，无新 flag 名。
- 两层结构（command 薄包装 + skill 真逻辑）不变。

## 7. 范围与未变

- 不新增命令 / 技能 / 钩子 / 概念（#27/#29 收口）。
- 运行时不变量 Out of scope（#30 已定）；覆盖率 / 快照属 test 轴但 v2 不强制（#28）。
- `init` / `note` 两命令 v2 不变。

## 8. 孵化 build 票（落地 hand-off，归 #32 派生）

真实 SKILL.md 改写不在此票，归以下 build 票（建议作为 #23 子票 / spec #22 构建票）：

- **B1 · review SKILL.md 重写**：`--axis` 解析（code/notes/test/types）+ 内化 tdd「好测试」定义（#28）+ 内化 code-review 评审准则与清单（#33）+ types 轴（#30）；同步 `commands/dsh-spec-review.md` 描述。
- **B2 · rot SKILL.md 重写**：`--check` 枚举扩展（simplify #29 + types #30）+ 工具链探测 + 阈值配置 + 跳过分支；输出格式沿用 v1 清单。
- **B3 · README + commands/*.md 同步**：四命令表补 `--axis` / `--check` 新枚举；更新命令描述。
