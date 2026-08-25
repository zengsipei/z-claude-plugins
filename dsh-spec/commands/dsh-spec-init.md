---
description: 在项目中脚手架化 dsh-spec 活文档与变更台账纪律（活文档 + 变更台账 + ADR 索引）。参数：[--root .] [--force]
allowed-tools: Read, Write, Edit, Bash
---

调用 `dsh-spec-init` skill，在消费项目根脚手架化以下结构：

- `SPEC.md`（产品视角规格摘要）
- `ARCHITECTURE.md`（改前必读的工程视角文档）
- `.agents/notes/{proposed,implemented,rejected}/<class>/`（变更台账目录树）
- `docs/adr/`（含 ADR 模板 `0000-template.md`）
- `.agents/LEDGER.md`（变更台账索引，以本插件 `dsh-spec/LEDGER.md` 为种子）

把用户参数原样传给 skill：`$ARGUMENTS`

若项目已初始化（`.agents/notes` 已存在），skill 会停下提示，除非用户显式传 `--force` 覆盖。
