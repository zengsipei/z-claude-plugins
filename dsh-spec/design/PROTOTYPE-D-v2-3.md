# dsh-spec v2 · 简化发现 rot 检查设计（PROTOTYPE — D-v2-3 #29）

> PROTOTYPE，非交付物。用于反应取舍。真实 SKILL.md 落地归 #32（命令/技能面与命名）派生的 build 票；本文件只定「`dsh-spec-rot --check simplify` 简化发现检查」的设计与判定清单。
> 锁定后：结论写入 #29 的 resolution comment 并关闭；本文件保留为设计史（build 票可并入或参考）。

## 背景约束（已锁定，无需重议）

- D-v2-1 (#27)：v2 收口 = 三大支柱设计 + 分工澄清；**支柱2 简化发现 = 仅 rot warn-only（knip/jscpd），不另起 review 轴**。三支柱执行模式已定，本票只在 rot 内设计该检查。
- R2 (#18)：不在 build 层（PreToolUse）硬阻断；rot 天生 warn-only、只报告不自动修（v1 已定）。
- R-v2-1 (#24)：dsh 真实简化发现 = knip（死代码/未用导出）+ jscpd（克隆检测，minLines 6 / minTokens 60）+ oxlint/sonarjs（重复分支/函数），CI 硬门禁。对文档/技能密集仓过重，且 dsh-spec 是**通用插件**，消费项目未必有该工具链。
- 通用兼容原则（同 R-v2-3 #26 思路）：无对应工具链则跳过，类比 v1 `tests`「无测试，跳过」。
- v1 rot 形态：`--check <all|docs|notes|tests|adr>`，默认 `all`；步骤 = 解析 --check → 逐查产出发现 → 输出按严重度排序清单。本票在其上增量，不另造结构。

## 决策摘要（设计建议，待 reaction）

简化发现以 **rot 第五查 `--check simplify`** 形态并入（warn-only、报告-only），分两层信号：**自包含层**（模块体积 LOC、单文件导出数，零依赖恒可跑）+ **工具增强层**（jscpd 重复、knip 死代码、sonarjs 圈复杂度，消费项目有工具才跑、无则跳过）；输出沿用 v1 发现清单，每条 = `{文件, 信号, 度量值, 建议}`。不新增命令/不新起 review 轴。

---

## 1. 检查信号与度量（Q1）

分两层，保证「通用插件 + 零依赖可跑 + 工具增强」：

**自包含层（零依赖，恒可跑 —— 纯 `git`/LOC/`grep`，不依赖消费项目工具链）**
- 模块体积：`*.ts`/`*.py`/`*.js` 单文件 **LOC > 阈值**（默认 warn 400 / 高 800）。
- 单文件导出数：`export` 数量 **> 阈值**（默认 20）→ 提示聚合同类导出或拆模块。

**工具增强层（消费项目本地有该工具才跑，无则标注「未配置 <tool>，跳过」，类比 v1 `tests`）**
- 重复片段：**jscpd**，沿用 dsh 默认（`minLines 6` / `minTokens 60`）。
- 死代码/未用导出：**knip**（若消费项目配了 knip）。
- 圈复杂度：**sonarjs / eslint complexity**（若消费项目有）→ 高复杂度函数提示抽函数。

**不纳入**（避免过重 / 与别轴重叠）：
- 快照、覆盖率（属 test 轴，D-v2-2）；
- 模块图校验、`verify-doc-budgets` 字数预算（dsh 专属 CI 重门禁，顺延 Out of scope）；
- 自动重构/自动修（rot 范围 = 只报告，v1 已定）。

阈值与工具集合设计为**可配**（rot 配置块 / `--simplify-thresholds`），有默认值、零配置可跑自包含层。

## 2. 输出形态（Q2）

沿用 v1 rot 的发现清单结构，每条 = **`{文件, 信号, 度量值, 建议}`**，报告-only、零自动修；「建议」为人工执行提示（类比 v1 note 归档建议）。按严重度（高→低）排序。

示例：
```
[简化发现] src/foo.ts — 模块体积 512 行（>400，warn）
  建议：按职责拆为 <A>/<B> 两个模块
[简化发现] src/bar.ts — 重复片段 jscpd（2 处 / ~18 行）
  建议：抽公共函数 <name>()
[简化发现] src/baz.ts — 导出 27 个（>20）
  建议：聚合同类导出或拆为子模块
[简化发现] 未配置 jscpd/knip，跳过工具增强层（自包含层已完成）
```

## 3. 与现有四查的并列 / `--check simplify` 是否合适（Q3）

- 加 `simplify` 进 `--check` 枚举：`--check <all|docs|notes|tests|adr|simplify>`，默认 `all` 含 simplify。
- **不新增命令、不新起 review 轴**（与 #27 一致：支柱2 仅 rot warn-only；test 轴才是 review 轴，D-v2-2）。
- 复用 v1 步骤结构（解析 --check → 逐查产出发现 → 输出排序清单）；工具增强层「无工具链」走 v1 `tests` 同款「跳过」分支。
- 与 docs 查边界：docs 查 `ARCHITECTURE.md` 声明漂移（结构一致性）；simplify 查复杂度增长（规模/重复信号），二者正交。

## 4. 范围外与遗留

- Stop 钩子接入 warn-only 语义（地图 Not yet specified）：本票不碰，待 #29/#30 收口后单独议（可能归入 #31 或新票）。
- 真实 SKILL.md 落地（参数枚举扩展、工具是否存在探测、阈值配置、输出格式）：归 #32 派生 build 票。
- 多项目/monorepo 隔离（#27 Out of scope 顺延）：本票按单上下文设计。

---

## 已锁定取舍（D-v2-3 设计结论 — Q1–Q3，待用户 reaction）

- **Q1（信号/度量）**：分两层 —— 自包含层（LOC>400 warn/800 高、导出>20）+ 工具增强层（jscpd 默认、knip 死代码、sonarjs 圈复杂度，有工具才跑、无则跳过）；不纳入快照/覆盖率/模块图；阈值可配有默认。
- **Q2（输出）**：沿用 v1 发现清单，每条 `{文件, 信号, 度量值, 建议}`，报告-only、按严重度排序、「建议」为人工提示。
- **Q3（并列/接入）**：`--check simplify` 进枚举、默认 all 含之；不新增命令/不新起 review 轴；复用 v1 步骤结构与「跳过」分支。

## 状态
- D-v2-3 (#29) 原型已起；结论按 Q1–Q3 推荐锁定，待用户 reaction 后由 #29 resolution 记录并关闭。
- 真实落地归 #32（命令/技能面与命名）派生 build 票；本文件保留为设计史。
