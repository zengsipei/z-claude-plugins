---
description: 把一次非平凡改动记入变更台账，生成 .agents/notes/<lifecycle>/<class>/<date>-<slug>.md。参数："<slug>" [--class feature|bug-fix|simplification|architecture|process|testing] [--lifecycle proposed|implemented|rejected] [--no-edit]
allowed-tools: Read, Write, Edit, Bash
---

调用 `dsh-spec-note` skill，为本次改动留一笔变更台账。

把用户参数原样传给 skill：`$ARGUMENTS`

skill 会：确定 slug/class/lifecycle → 生成 `.agents/notes/<lifecycle>/<class>/<date>-<slug>.md`（必含 `## Problem` / `## Decision|Proposal` / **必填** `## Alternatives considered` / `## Consequences`）→ 打开 `$EDITOR` 补全或逐节索取 → 在 `.agents/LEDGER.md` 对应节追加索引。
