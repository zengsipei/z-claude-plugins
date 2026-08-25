---
name: dsh-spec-note
description: 把一次非平凡改动记入变更台账，生成 .agents/notes/<lifecycle>/<class>/<date>-<slug>.md。当用户说「记一笔」「加 note」「留账」，或完成 feature/bug-fix/simplification/architecture/process/testing 改动时调用。
---

# dsh-spec-note

每个非平凡改动对应一条 note，保证项目可追责、可回溯。

## 参数

- `"<slug>"`：位置参数，kebab-case、纯 ASCII 小写、去空格与停用词、≤40 字符、禁中文/大写。例：`add-retry-backoff`。
- `--class <feature|bug-fix|simplification|architecture|process|testing>`：默认 `feature`。
- `--lifecycle <proposed|implemented|rejected>`：默认 `implemented`；计划阶段用 `proposed`。
- `--no-edit`：跳过 `$EDITOR` 补全，直接生成骨架等用户填。

## 步骤

1. 解析 `<slug>`、`--class`、`--lifecycle`（默认 feature / implemented）。
   - 完成判定：slug、class、lifecycle 已确定；slug 满足 kebab-case ASCII≤40 约束，否则提示重命名。
2. 取 `<date>` 为今天（YYYY-MM-DD），拼出路径 `.agents/notes/<lifecycle>/<class>/<date>-<slug>.md`（lifecycle 在 class 在外）。若父目录不存在则创建。
   - 完成判定：目标路径已确定且目录就绪。
3. 写入 note，frontmatter + 正文五段（模板见下）。以下章节须全部填实：
   - `Status: <lifecycle>`（frontmatter 唯一字段）
   - `## Problem`（必填）——改动缘起。
   - `## Decision`（implemented/rejected）或 `## Proposal`（proposed）（必填）——改动本身。
   - `## Alternatives considered`（**必填**，哪怕只列「什么都不做」）——至少一条被否决的备选及其落选原因。
   - `## Consequences`（仅 implemented）——收益或代价。
   - 完成判定：文件存在且每节有内容；`## Alternatives considered` 非空。
4. 若设了 `$EDITOR` 且未传 `--no-edit`，打开该文件由用户补全；否则逐节向用户索取。
   - 完成判定：用户已填实或确认内容。
5. 在 `.agents/LEDGER.md` 对应 `<class>` 节追加/更新一行（日期倒序）：
   `- [<date>] <slug> — <一句话摘要> · <lifecycle>`，链接指向 note 文件。若节不存在则新建。
   - 完成判定：台账已索引此 note。

## 范围

只负责记录。评审由 `/dsh-spec-review` 负责，归档（v1）由 `/dsh-spec-rot` 建议 + 人工确认执行（沿用 `archived/<class>/` + `Archived:` 头，proposed/implemented/rejected 三态整体迁入）。

---

## note 模板

```markdown
---
Status: <proposed|implemented|rejected>
---

## Problem
<改动缘起>

## Decision
<改动本身（implemented / rejected 用此节）>

## Proposal
<改动方案（proposed 用此节）>

## Alternatives considered
- <备选 A>：<为何不选>
- <备选 B>：<为何不选>

## Consequences
<收益或代价（仅 implemented）>
```
