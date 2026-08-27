---
description: 把一次非平凡改动记入变更台账，生成 .agents/notes/<lifecycle>/<class>/<date>-<slug>.md。参数："<slug>" [--class feature|bug-fix|simplification|architecture|process|testing] [--lifecycle proposed|implemented|rejected] [--no-edit]
allowed-tools: Read, Write, Edit, Bash
---

调用 `dsh-spec-note` skill 处理。把用户参数原样传给 skill：`$ARGUMENTS`

参数与 note 模板的权威说明见 `skills/dsh-spec-note/SKILL.md` 与 `.agents/RULES.md`（或插件母本 `RULES.md`）。
