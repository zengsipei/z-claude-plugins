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
2. 把标准评审委派给本仓库已有的 `code-review` skill：以 `--since` 解析出的固定点（commit/branch/tag/merge-base，默认上次 merge-base）作为 code-review 的「固定点」传入，范围同为自该点起到 HEAD 的三点 diff。code-review 会并行跑 Standards / Spec 两轴，本 skill 不重造其逻辑，只消费结论。
   - 接口方式：通过 `Skill` 工具按名调用 `code-review`（命令 `/dsh-spec-review` 的 `allowed-tools` 已含 `Skill`）；将上一步确定的固定点作为 code-review 的固定点原样传入，不另起一套评审实现。
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

只审计与闸门。触发位置分两层（D3 #18）：
- **权威闸口** = 本命令 `/dsh-spec-review --gate strict`（默认）：由人触发，合并前跑。
- **提醒闸口** = `Stop` hook（`hooks/dsh-spec-gate.py`）：会话级 warn-only 提醒，工作树有改动却未建 note/ADR 时 stderr 提示、零退出、不阻断。

评审逻辑本身不在此实现，复用 `code-review`。精确逐 commit↔note 匹配归本命令的 step 3。

### v1 不接入 `tdd`（测试不变量轴留 v2）

测试不变量是六大支柱之一、明确列为 v2 范围（地图 Notes / Out of scope）。v1 的评审/预推闸门**只覆盖两件事**：`code-review` 标准评审 + 逐改动 note/ADR 审计。本命令与 `Stop` hook 均**不调用 `tdd`**；未来若加「测试不变量」轴，可新增 `--axis test` 复用 `tdd`，不在本次落地。
