---
name: dsh-spec-review
description: 合并前闸门——跑 code-review skill，再审计自 --since 起的每个非平凡改动是否都有对应 note/ADR。当用户说「评审」「合并前检查」「跑闸门」，或准备合并时调用。
---

# dsh-spec-review

合并闸门：标准评审 + dsh-spec「无 note 不合并」审计。复用现有 `code-review` skill，不重造评审逻辑。

## 参数

- `--since <ref>`：审计起点，默认上次 merge base（如 `$(git merge-base HEAD origin/main)` 或最近一次 merge commit）。
- `--gate <strict|warn>`：默认 `strict`。`strict` 缺 note 即报错阻断；`warn` 仅提醒、零退出。

## 步骤

1. 解析 `--since`（默认上次 merge base）与 `--gate`（默认 strict）。
   - 完成判定：两者已确定。
2. 把评审委派给本仓库已有的 `code-review` skill，范围相同（自 `--since` 起的改动）。
   - 完成判定：`code-review` 已产出结论。
3. 枚举 `--since` 起的每个非平凡改动（比对 `git log --since`），逐个确认 `.agents/notes/` 或 `docs/adr/` 中存在对应记录（按改动主题/文件匹配 note slug 或 ADR）。
   - 完成判定：每个改动已匹配到 note/ADR，或列入缺口清单。
4. 按 `--gate` 处置缺口：
   - `strict`：报告缺口并以非零退出，阻断合并。
   - `warn`：仅列缺口提醒，零退出。
   - 完成判定：闸门结论已给出；strict 下遇缺口即停。
5. 汇总：code-review 结论 + note 审计结果，给出单一结论（通过 / 阻断）。
   - 完成判定：用户拿到单一结论。

## 范围

只审计与闸门。闸门触发位置（D3 #18）由 hook 决定；评审逻辑本身不在此实现，复用 `code-review`。
