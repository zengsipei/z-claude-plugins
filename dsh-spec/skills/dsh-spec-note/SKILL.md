---
name: dsh-spec-note
description: 把一次非平凡改动记入变更台账，生成 .agents/notes/<lifecycle>/<class>/<date>-<slug>.md。当用户说「记一笔」「加 note」「留账」，或完成 feature/bug-fix/simplification/architecture/process/testing 改动时调用。
---

# dsh-spec-note

每个非平凡改动对应一条 note，保证项目可追责、可回溯。

## 参数

- `"<slug>"`：位置参数，约束见 `.agents/RULES.md` §3（例：`add-retry-backoff`）。
- `--class <class>`：默认 `feature`；枚举读 `.agents/RULES.md` §1。
- `--lifecycle <lifecycle>`：默认与语义见 `.agents/RULES.md` §2。
- `--no-edit`：跳过 `$EDITOR` 补全，直接生成骨架等用户填。

## 步骤

1. 解析 `<slug>`、`--class`（默认 feature）、`--lifecycle`（默认值见 `.agents/RULES.md` §2）。
   - 完成判定：slug、class、lifecycle 已确定；slug 通过 `.agents/RULES.md` §3 约束校验，不合格提示重命名、不静默修正。
2. 取 `<date>` 为今天（YYYY-MM-DD），按 `.agents/RULES.md` §4 的路径模式拼出 note 路径（lifecycle 在外、class 在内）。若父目录不存在则创建。
   - 完成判定：目标路径已确定且目录就绪。
3. 写入 note（用下方「note 模板」落盘）。frontmatter 与必填节规则以 `.agents/RULES.md` §5 为准；frontmatter 除 `Status:` 外唯一允许的其它字段是 `Archived:`（§9 归档协议）。
   - 完成判定：文件存在，§5 列明的必填节均填实。
4. 若设了 `$EDITOR` 且未传 `--no-edit`，打开该文件由用户补全；否则逐节向用户索取。
   - 完成判定：用户已填实或确认内容。
5. 在 `.agents/LEDGER.md` 对应 `<class>` 节追加/更新一行（日期倒序）：
   `- [<date>] <slug> — <一句话摘要> · <lifecycle>`，链接指向 note 文件。若节不存在则新建。
   - 完成判定：台账已索引此 note。

## 范围

只负责记录。评审由 `/dsh-spec-review` 负责，归档由 `/dsh-spec-rot` 建议、人工确认执行——归档协议整体见 `.agents/RULES.md` §9。

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
<收益或代价——必填与否按 `.agents/RULES.md` §5 裁定>
```
