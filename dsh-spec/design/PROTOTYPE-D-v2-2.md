# dsh-spec v2 · 测试不变量轴设计（PROTOTYPE — D-v2-2 #28）

> PROTOTYPE，非交付物。用于反应取舍。真实 SKILL.md 落地归 #32（命令/技能面与命名）派生的 build 票，本文件只定「`--axis test` 测试不变量轴」的设计与判定清单。
> 锁定后：结论写入 #28 的 resolution comment 并关闭；本文件保留为设计史（build 票可并入或参考）。

## 背景约束（已锁定，无需重议）

- R-v2-1 (#24)：dsh 真实纪律 = 每文件 100% 覆盖率 + 无密钥快照回放 + 运行时不变量；但属 CI 硬门禁，对文档/技能密集仓过重。
- R-v2-2 (#25)：`/dsh-spec-review --axis test` 复用 `tdd` 可行；`tdd` 是「开发期 red-green 指南」，**不生审计报告、不接受 diff 参数**，故应作「判定标准库」而非执行器。
- R-v2-3 (#26)：强类型门禁归 D-v2-4；本票不涉及。
- D-v2-1 (#27)：v2 收口 = 三大支柱设计 + 分工澄清；支柱1 测试不变量 = **必做 review 轴 `--axis test`（人触发、可 strict）**；rot `tests` 升级 Out of scope。
- #28 重开（v2 自包含铁律 #31 / #33）：原 Q2「经 Skill 调 `tdd`」改为**内化 `tdd` 定义**进本 rulebook；pillar 设计（Q1/Q3/Q4/Q5/Q6）不变。详见 §2。

## 决策摘要（设计建议，待 reaction）

测试不变量以**第三兄弟闸门步骤**形态并入 `/dsh-spec-review`：复用 `--since` 固定点，借 `tdd` 的「好测试」定义作判定标准，自实现 seam 测试存在性 + 反模式审计；不跑测试套件、不强制覆盖率、不比快照。

---

## 1. 轴模型：`--axis` 统一选择（Q1）

v1 的 `/dsh-spec-review` 隐式跑 `code`（委派 code-review）+ `notes`（note/ADR 审计）两轴。v2 显式化为 `--axis`：

- `--axis <all|code|spec|notes|test>`，默认 `all`。
  - `code` → 委派 `code-review` skill（Standards/Spec 两轴不变，其内部逻辑）。
  - `notes` → 现有 step3 note/ADR 审计。
  - `test` → **本票新增** seam 测试审计（§3）。
- 向后兼容：v1 行为 = `code,notes`；v2 默认 `all` = `code,notes,test`。未就绪团队用 `--axis code,notes` 退出测试轴。
- `--gate <strict|warn>` 对所有选中轴统一生效（含 test）。

> 不在 code-review 内部注入第三轴；test 是 dsh-spec-review 自身兄弟闸门步骤，仅共享固定点。

## 2. tdd 复用边界：判定标准库（化用），非执行器、非运行时依赖（Q2）

`--axis test` 的步骤：
1. **内化** `tdd` 的「好测试」定义（seam 概念 + 三类反模式，见 §4）进 `dsh-spec-review` 自身 rulebook，作为判定标准；**不**经 `Skill` 工具运行时调 `tdd`。理由：v2 自包含铁律（#31 / #33）要求插件运行时零外部技能依赖，复用 = 化用（吸收进自身规则书，而非运行时引用外部技能）。
   - 测试应经**公开接口**验证行为，而非实现细节（重构成败不应让测试红）。
   - 三类反模式（见 §4）：实现耦合 / 同义反复 / 水平切片。
2. 审计逻辑由 `dsh-spec-review` **自实现**（类比 step3 note 审计）。

> 与原初版差异（#28 重开）：v1 预留「`--axis test` 复用 `tdd`」改为**内化** tdd 定义；`allowed-tools` 中 `Skill` 仅为 code 轴委派 `code-review` 保留，test 轴不再运行时调 `tdd`。（后经 #33，code 轴亦内化、不再委派，`Skill` 仅存「外部技能在场可选增强」用途。）

## 3. 审计逻辑（自实现，Q3 + Q4）

输入：`git diff <since>...HEAD`（`--since` 默认上次 merge-base，与 code/notes 轴同固定点）。

枚举每个**非测试源码改动**：
- 范围：脚本 / `hooks/*.py` / `*.ts` 等可执行源码；**排除** `.md`、skill 文本、spec、docs（文档密集仓不脆断）。
- 测试文件本身不在审计对象内。

对每个改动检查「测试不变量成立」判定清单：
1. 在预约定 **seam**（借 tdd 的 seam 概念：公开接口处）有对应测试 —— 即「新代码须带测试」。
2. 该测试**不命中**三类反模式（实现耦合 / 同义反复 / 水平切片）。

不采纳：
- 覆盖率硬阈值（文档/技能密集仓会脆断，且 dsh 100% 门槛过重）。
- 快照比对（无运行态快照，不适用）。

理由：seam 测试存在性 + 反模式过滤已足以表达「改动不退化测试」的不变量，且零新增依赖、零阈值维护。

## 4. 「好测试」判定标准（源自 tdd，Q4 反模式集）

| 反模式 | 含义 | 判定信号 |
|---|---|---|
| 实现耦合 | mock 内部协作者 / 测私有方法 / 绕过公开接口验证 | 重构内部实现而行为未变时测试红 |
| 同义反复 | 断言显而易见、镜像实现（assert 恒真或仅复述代码） | 测试通过但不约束任何行为 |
| 水平切片 | 先写全部测试再写全部实现（bulk RED→bulk GREEN） | 测试基于「想象行为」而非当前实现，对真实变更不敏感 |

> 前两项由 tdd SKILL「Bad tests」段直接支撑；水平切片由 tdd「Anti-Pattern: Horizontal Slices」段支撑。三类即 §3 判定清单②的审查维度。

## 5. 强制形态（Q5）

- review 轴：人触发、合并前跑；**不** PreToolUse 硬阻断（R2 #18 硬约束）。
- `--gate strict`：test 缺口即非零退出，阻断合并**决定**（人仍拍板）。
- `--gate warn`：仅列缺口提醒，零退出。
- 与 notes 轴共享同一 `--gate` 处置。

## 6. 与 rot `tests` / code-review 的边界（Q6）

- `dsh-spec-rot --check tests`：保持 v1「有测试则跑、记录退化、无则跳过」warn-only，**不升级**（#27 Out of scope）。
- `code-review`：Standards/Spec 两轴不变；test 轴是其外兄弟闸门步骤，不向 code-review 注入第三轴。
- 分工：rot 管「测试是否退化」（运行态），review `--axis test` 管「新改动是否带好测试」（设计态）。二者正交。

## 7. 范围外与遗留

- 不跑测试套件、不强制覆盖率、不比快照（见 §3）。
- Stop 钩子接入方式（warn-only）属地图 Not yet specified，待 #29/#30 收口，不在本票。
- 真实 SKILL.md 落地（参数解析、seam 默认约定、输出格式）归 #32 派生 build 票。

---

## 已锁定取舍（D-v2-2 设计结论 — Q1–Q6，用户授权自主推进）

- **Q1**：新增 `--axis <all|code|spec|notes|test>`，默认 `all`（含 test）；v1 行为=`code,notes`，未就绪用 `--axis code,notes` 退出。
- **Q2**：tdd 作判定标准库（**内化**其「好测试」定义进本 rulebook，运行时零外部 `tdd` 技能依赖；复用=化用，自包含铁律）；审计自实现（类比 step3）。
- **Q3**：审计对象 = `git diff <since>...HEAD` 非测试源码改动，排除 .md/skill 文本/spec/docs。
- **Q4**：判定清单 = ①seam 有对应测试（新代码须带测试）②不命中三类反模式；不采纳覆盖率/快照。
- **Q5**：review 轴、人触发、合并前；`--gate strict` 缺口即非零退出（不 PreToolUse）；`--gate warn` 仅报告。
- **Q6**：rot `tests` 保持 v1 warn-only 不升级；code-review 两轴不变；test 轴是兄弟闸门步骤。

## 状态
- D-v2-2 (#28) 原型已起；结论按 Q1–Q6 锁定，其中 Q2 经 #28 重开改为**内化 tdd 定义**（自包含铁律），已由 #28 resolution 记录并关闭。
- 真实落地归 #32（命令/技能面与命名）派生 build 票；本文件保留为设计史；与 #33 内化 code-review 同文件同次 build 落地 `dsh-spec-review` SKILL.md（真实 `--axis test` 参数解析 / seam 默认约定 / 输出格式）。
