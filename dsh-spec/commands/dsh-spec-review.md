---
description: 合并前闸门——跑 code-review skill，再审计自 --since 起的每个非平凡改动是否都有对应 note/ADR。参数：[--since <ref>] [--gate strict|warn]
allowed-tools: Read, Grep, Bash, Skill
---

调用 `dsh-spec-review` skill，作为合并前闸门。

把用户参数原样传给 skill：`$ARGUMENTS`

skill 会：委派本仓库已有的 `code-review` skill 做标准评审 → 枚举 `--since`（默认上次 merge）起的每个非平凡改动，逐个核对 `.agents/notes/` 或 `docs/adr/` 是否存在对应记录 → 按 `--gate`（strict|warn）处置缺口（strict 缺 note 即报错阻断，warn 仅提醒）→ 汇总单一结论（通过 / 阻断）。评审逻辑复用 `code-review`，不重造。
