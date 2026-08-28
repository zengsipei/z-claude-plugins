# Debug 与 Script 独立工作流

Debug 和 Script 不走 Design → Implement → Test，也不补建标准设计、施工或测试文档。两者分别以 `Debug排查记录.md`、`脚本任务.md` 作为唯一人类主文档；计划、决定、执行、文件改动、验证和结论都写回该文档。`status.md`、`summary.md` 与 `onlyAI/` 继续承担通用状态、收口摘要和原始证据职责。

## Debug：按授权排查或修复

Debug 支持两种授权：

- `diagnose`：定位根因并给出建议，不修改代码。
- `fix`：定位根因后实施修复并验证。只有用户明确要求修复时才进入。

执行流程：

1. 先确认授权是 `diagnose` 还是 `fix`。独立任务使用 `init --phase debug --debug-mode diagnose|fix`；标准 SDLC 中临时插入排查时使用 `start --phase debug --debug-mode diagnose|fix`，但仍只生成 Debug 文档。
2. 使用 `assets/Debug排查记录模板.md` 创建或更新 `Debug排查记录.md`，记录授权范围、现象、复现和影响。
3. 收集错误、日志、版本、调用链和最小复现，建立假设并逐项用证据排除或确认；不要用 Grill 代替技术调查。
4. 根因必须有可复现或可验证证据。无法确认时记录阻塞条件，不把“最可能”写成结论。
5. 仅在存在方案选择、公共契约/数据结构变化、临时止血与长期修复取舍，或涉及性能、安全、生产数据、兼容和扩大文件边界时执行 Grill-with-docs；开始评审时运行 `review --status in_progress`。
6. 每个选择立即回写 Debug 文档的方案、决定、文件边界和风险；未确认项归零后运行 `review --status completed --evidence [评审记录]`，再实施修复。
7. `diagnose` 在根因、证据和建议完整后结束。`fix` 继续在同一文档记录实际操作、文件改动、原复现路径、相关回归和边界验证。
8. 原始命令和长输出写入 `onlyAI/operations-log.md`、`onlyAI/verification.md`，但不能替代 Debug 文档中的可读记录。
9. 使用 `update --state` 驱动合法转换：`diagnose` 为 `investigating → root_cause_confirmed`，`fix` 为 `investigating → root_cause_confirmed → [reviewing] → fixing → awaiting_verification → verified`。写入 `root_cause_confirmed` 或 `verified` 时必须附 `--evidence`；`diagnose` 达到根因确认、`fix` 达到验证完成，且主文档已定稿、未确认项为 `0` 时运行 `complete`。迁移任务的模式不明确时先运行 `configure-debug --mode diagnose|fix`。

独立 Debug 完成后进入 `sdlc-close`；未单独执行 `sdlc-test` 时按 Close 的风险提醒与二次确认收口。标准 SDLC 中临时插入的 Debug 完成后必须返回保存的原阶段继续验证，不能从 Debug 直接关闭或借此跳过原流程。

## Script：在单一文档内计划、执行和验证

1. 确认脚本类型、目标环境、风险、数据范围、授权和任务目录，使用 `init --phase script --script-risk low|medium|high --script-environment local|test|staging|production`。迁移任务缺少这些信息时先运行 `configure-script`。
2. 使用 `assets/脚本任务模板.md` 创建 `脚本任务.md`；脚本正文、执行计划、实际执行、改动和验证全部记录在同一文档，SQL 放入 `sql/`。
3. 评估风险：

| 风险 | 示例 | Grill-with-docs |
|---|---|---|
| 低 | 本地只读统计、测试数据导出、完全可逆 | 有待确认项时执行 |
| 中 | 预发写操作、可回滚迁移、非核心批处理 | 强制执行 |
| 高 | 生产写操作、核心数据、不可逆或大批量操作 | 强制执行，生产前另行批准 |

4. 中高风险评审至少覆盖影响量、Dry-run、副作用、幂等、批次限速、并发锁、中断恢复、备份、回滚、超时、停止条件、审计和前后验证。
5. 中高风险脚本用 `review --status in_progress` 开始评审。每个决定同步更新脚本文档、脚本正文、回滚方案和执行计划；未确认项归零后用 `review --status completed --evidence [评审记录]` 留痕，才能标记“可执行”。
6. 先在测试或预发环境验证；高风险脚本必须具备 Dry-run、分批、备份和经过验证的回滚方案。
7. 生产执行是独立授权门禁。“可执行”不等于已经获得生产执行许可。Script 不由 Solo 推进；生产执行须用户另行批准。进入 `awaiting_approval` 后，必须用 `approve-script --evidence [用户批准]` 留痕，才能进入 `executing`。批准 SDLC 或 AI 登记写入不等于批准业务数据库或生产写入。
8. 使用 `update --state` 驱动合法转换。普通成功路径为 `in_progress → [reviewing] → [awaiting_approval] → executing → verified`；失败并完成恢复时为 `executing → rolled_back`。写入 `verified` 或 `rolled_back` 时必须附 `--evidence`。
9. 仅完成脚本设计而未执行时保持“待批准/待执行”，不能运行 `complete`。达到用户约定目标并验证成功，或已验证回滚完整，且文档定稿、未确认项为 `0` 后运行 `complete`。

Script 完成后进入 `sdlc-close`；未单独执行 `sdlc-test` 时按风险提醒与用户二次确认关闭。Close 只校验 `脚本任务.md`，不要求标准设计、施工或测试文档。Debug、Script 都没有 Solo 模式，不能借 Solo 绕过专项授权或执行门禁。

Debug、Script 完成 `complete` 后由状态脚本投影为 `debug|script / 已完成 / 90%`，Close 通过后为 `done / 已关闭 / 100%`；不得用 `update` 伪造“待关闭”或最终状态。

Debug、Script 交付前都运行状态脚本 `validate`。
