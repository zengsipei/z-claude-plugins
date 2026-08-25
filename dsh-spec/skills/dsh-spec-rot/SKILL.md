---
name: dsh-spec-rot
description: 漂移与一致性巡检——发现文档漂移、无 note 的 commit、测试退化、ADR 过期。当用户说「巡检」「漂移检查」「rot 检查」，或按时触发时调用。
---

# dsh-spec-rot

及早暴露腐烂，便于低成本修复。只报告，不自动修复。

## 参数

- `--check <all|docs|notes|tests|adr>`：默认 `all`。可多选（逗号分隔）。

## 步骤

1. 解析 `--check`（默认 all），展开为检查集合。
   - 完成判定：检查集合已确定。
2. 对每个选中的检查产出发现：
   - `docs`：`ARCHITECTURE.md` 声明的模块/不变量/契约与实际代码结构（文件、导出、依赖）漂移。
   - `notes`：自上次 note（`.agents/LEDGER.md` 最新日期）起的 `git log` commit 无对应 `.agents/notes` 条目。
   - `tests`：若项目存在测试套件则运行，记录退化（失败/跳过增多）；无测试则标注「无测试，跳过」。
   - `adr`：ADR 被推翻但未标 `superseded-by`/`rejected`，或其关联代码已不符。
   - 完成判定：每个选中检查要么有发现列表，要么标记 ok。
3. 输出按严重度（高→低）排序的清单，含文件与具体漂移点；对可自动归档的 note（proposed/implemented/rejected 三态齐备且已落地）给出「建议归档」提示（人工确认执行，沿用 `archived/<class>/` + `Archived:` 头）。
   - 完成判定：用户拿到可处理的腐烂报告。

## 范围

只检测与建议。修复走正常改动 + `/dsh-spec-note`。完整检查项后续 ticket 扩充（见地图 Not yet specified）；本技能先交付上述 v1 集合。
