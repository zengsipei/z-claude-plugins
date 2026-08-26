---
description: 合并前闸门——多轴评审（code 标准评审 / notes 台账审计 / test seam 测试审计 / types 类型退化审计）。参数：[--since <ref>] [--gate strict|warn] [--axis <all|code|notes|test|types>]
allowed-tools: Read, Grep, Bash, Skill
---

调用 `dsh-spec-review` skill，作为合并前闸门。

把用户参数原样传给 skill：`$ARGUMENTS`

skill 会：按 `--axis`（默认 `all` = code,notes,test,types；支持逗号组合，`--axis code,notes` 精确复现 v1 行为；非法值报错）依次执行四条轴——**code**：Standards/Spec 两轴标准评审（准则内化，零外部技能依赖；外部 `code-review` 在场仅可选增强）；**notes**：枚举 `--since`（默认上次 merge base）起的每个非平凡改动，逐个核对 `.agents/notes/` 或 `docs/adr/` 是否存在对应记录；**test**：审计 diff 中非测试源码改动的 seam 测试存在性 + 三类反模式（实现耦合/同义反复/水平切片，判定标准内化；不跑套件、不强制覆盖率、不比快照）；**types**：类型退化审计（自包含 grep 气味层 + 工具增强层，复用消费项目 linter，回退 tsc → Biome → ESLint；无工具链静默跳过、绝不装包）→ 按 `--gate`（strict|warn，默认 `strict`，对所有选中轴统一生效）处置缺口（strict 任意轴缺口即非零退出阻断，warn 仅提醒）→ 汇总单一结论（通过 / 阻断）。四轴共用同一 `--since` 固定审计窗口。
