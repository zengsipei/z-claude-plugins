# 确定性任务状态

`docs/[任务目录]/onlyAI/task-state.json` 是工作流、阶段、门禁和进度的机器事实源；`status.md` 是面向人的可读投影与状态日志。所有状态变化通过 `scripts/task_state_core.py` 完成，不得手工改写 `status.md` 顶部的系统、任务、工作流、阶段、状态、文档状态、未确认项、进度和更新时间。人工说明、登记结果、知识库同步结果等正文仍写入 `status.md`。

`workflow` 取值为 `standard`、`debug`、`script`。它决定 Close 校验哪一组人类主文档，不能靠补空白文档切换工作流。Schema v3 还用 `review`、`phase_evidence`、`debug_mode`、`script` 和 `close.artifacts` 保存评审、授权、执行与收口证据；v1/v2 状态由脚本兼容升级。

## 目录

- [初始化与迁移](#初始化与迁移)
- [阶段内更新](#阶段内更新)
- [标准阶段转换](#标准阶段转换)
- [Close 转换](#close-转换)
- [校验](#校验)

## 初始化与迁移

将下列 `<state-script>` 替换为当前 skill 中 `scripts/task_state_core.py` 的实际路径：

```powershell
python <state-script> init --task-dir docs/[任务目录] --system [系统] --title [任务]
python <state-script> init --task-dir docs/[任务目录] --system [系统] --title [任务] --phase debug --debug-mode diagnose|fix
python <state-script> init --task-dir docs/[任务目录] --system [系统] --title [任务] --phase script --script-risk low|medium|high --script-environment local|test|staging|production
```

已有 `status.md` 但没有机器状态的旧任务不得覆盖初始化：

```powershell
python <state-script> migrate --task-dir docs/[任务目录]
python <state-script> show --task-dir docs/[任务目录]
# 对照既有文档复核并按需 update 后：
python <state-script> migration-review --task-dir docs/[任务目录] --note "已核对旧状态与现有产物"
# 旧状态位于 test / close 时还必须明确测试事实；通过结论必须附证据：
python <state-script> migration-review --task-dir docs/[任务目录] --test-state passed --evidence "003-测试文档.md：通过"
```

旧状态位于 `test` / `close` 时，迁移结果使用 `unknown` 防止把失败或部分执行误判为“未测试”；复核时必须通过 `--test-state not_started|passed|conditional|failed` 明确事实，有条件通过还需要 `--risk-accepted`。旧 `close` 状态会安全回退到 `test`，再重新执行关闭门禁。旧版机器状态在内存中按阶段和现有主文档推断 `workflow`：完整 Standard 设计/施工文档优先于遗留 Debug 文档，防止临时排查记录改变原工作流；下一次成功提交时升级保存。迁移复核完成前，脚本拒绝开始阶段、完成阶段、登记施工任务、写入测试结论和关闭任务。

## 阶段内更新

```powershell
# 文档评审与未确认项
python <state-script> update --task-dir docs/[任务目录] --document-state reviewing --open-items 2 --note "进入 Grill 评审"
python <state-script> review --task-dir docs/[任务目录] --status in_progress --note "开始 Grill 评审"
python <state-script> update --task-dir docs/[任务目录] --open-items 0 --note "决定已回写"
python <state-script> review --task-dir docs/[任务目录] --status completed --evidence "[主文档评审记录或一致性检查]"
python <state-script> update --task-dir docs/[任务目录] --document-state final --note "文档定稿"
python <state-script> update --task-dir docs/[任务目录] --document-state ready --note "施工压测完成，可开始编码"

# 阻塞与解除
python <state-script> update --task-dir docs/[任务目录] --add-blocker "等待外部契约" --note "阶段阻塞"
python <state-script> update --task-dir docs/[任务目录] --resolve-blocker "等待外部契约" --note "外部契约已确认"

# Debug / Script 的关键终态必须附证据
python <state-script> update --task-dir docs/[任务目录] --state root_cause_confirmed --evidence "[根因证据]"
python <state-script> update --task-dir docs/[任务目录] --state verified --evidence "[验证证据]"
```

`open_items > 0` 或存在阻塞项时不能完成阶段。状态脚本还会扫描当前主文档及可选设计评审记录，发现“待决策”“待确认”“未开始”“待执行”“待验证”“阻塞”等当前阶段未完成状态时拒绝完成；不能只把 `open_items` 改为 `0`。设计文档必须为 `final`；Implement 的施工文档必须完成 `review` 并记录证据，先达到 `ready` 才能开始编码，完成状态只能使用 `complete`；Debug 诊断至少为 `root_cause_confirmed`、修复至少为 `verified`；Script 必须为 `verified` 或已验证的 `rolled_back`。Debug/Script 的关键结论同时写入 `phase_evidence`、各自主文档和 `onlyAI/verification.md`，不为此创建标准测试文档。

独立流程初始化时必须明确授权与风险。迁移的旧状态用配置命令补齐：

```powershell
python <state-script> configure-debug --task-dir docs/[任务目录] --mode diagnose|fix
python <state-script> configure-script --task-dir docs/[任务目录] --risk low|medium|high --environment local|test|staging|production
```

中高风险 Script 必须完成 `review`；生产 Script 进入执行前还必须单独记录批准：

```powershell
python <state-script> review --task-dir docs/[任务目录] --status in_progress
python <state-script> review --task-dir docs/[任务目录] --status completed --evidence "[脚本评审记录]"
python <state-script> update --task-dir docs/[任务目录] --state awaiting_approval
python <state-script> approve-script --task-dir docs/[任务目录] --evidence "[用户生产执行批准]"
python <state-script> update --task-dir docs/[任务目录] --state executing
```

从标准阶段插入 Debug 时，脚本保存原阶段的文档状态、进度、未确认项和阻塞上下文。仅诊断完成后原样恢复；修复并验证后回到原阶段重新验证，若原阶段为失败的 Test，则恢复为 `running` 并等待重新执行测试。

## 标准阶段转换

```powershell
# 完成当前 design-1 / design-2 / implement / debug / script
python <state-script> complete --task-dir docs/[任务目录]

# 只允许 design-1 → design-2 → implement → test；完成 Debug 后可返回原阶段
python <state-script> start --task-dir docs/[任务目录] --phase design-2
python <state-script> start --task-dir docs/[任务目录] --phase implement
python <state-script> start --task-dir docs/[任务目录] --phase test
python <state-script> start --task-dir docs/[任务目录] --phase debug --debug-mode diagnose|fix

# Implement：完成状态必须附实际验证证据
python <state-script> task --task-dir docs/[任务目录] --id T-01 --status in_progress --next-task T-01
python <state-script> task --task-dir docs/[任务目录] --id T-01 --status completed --evidence "python -m unittest ..." --clear-next

# Test：passed / conditional 必须附证据；conditional 还必须显式接受遗留风险
python <state-script> test --task-dir docs/[任务目录] --result passed --evidence "12 passed"
python <state-script> test --task-dir docs/[任务目录] --result conditional --risk-accepted --evidence "已记录已知限制"
```

测试失败写入阻塞并拒绝关闭。不能用 `update` 伪造 `completed`、`awaiting_close`、`closed`，也不能改写已关闭任务。

## Close 转换

`close-request` 根据 `workflow` 校验主文档：Standard 使用聚合设计/施工/测试文档，Debug 只使用 `Debug排查记录.md`，Script 只使用 `脚本任务.md`。除文件存在与机器状态外，还会扫描文档残留的未解决状态；`close-complete` 会再次扫描，防止 Close 期间重新引入待办。标准流程中临时插入的 Debug 必须先返回原阶段。

测试通过或有条件通过且风险已接受时：

```powershell
python <state-script> close-request --task-dir docs/[任务目录]
# 完成 summary.md、登记和知识沉淀，并逐项记录实际结果后
python <state-script> close-artifact --task-dir docs/[任务目录] --name summary --status completed --evidence "summary.md 已完成"
python <state-script> close-artifact --task-dir docs/[任务目录] --name registration --status skipped --evidence "[无可信 sessionId，已跳过]"
python <state-script> close-artifact --task-dir docs/[任务目录] --name knowledge --status local_only --evidence "[结论已沉淀到 summary.md]"
python <state-script> close-complete --task-dir docs/[任务目录]
```

登记状态也可按实际结果使用 `synced` 或 `failed`；知识沉淀状态也可使用 `synced` 或 `failed`。

测试完全未执行时，`close-request` 输出警告和一次性 `confirmation_token`。必须把风险告知用户并获得其明确二次确认；`close-request` 到 `close-confirm` 之间工作树不能变化：

```powershell
python <state-script> close-confirm --task-dir docs/[任务目录] --token [confirmation_token] --note "用户已明确确认跳过测试并关闭"
python <state-script> close-complete --task-dir docs/[任务目录]
```

不得把 token 暴露给用户后自行代替用户确认，也不得在 `close-request` 到 `close-confirm` 之间工作树变化后复用旧 token。该窗口内工作树变化会撤销待确认状态；必须重新验证受影响阶段、完成该阶段并重新发起关闭。用户确认后不再绑定工作树指纹，但跳过测试的事实、风险、确认与结论必须写入 `summary.md` 和状态记录。`close-complete` 要求 `summary.md` 存在，并要求 summary、AI 登记和知识沉淀三个 artifact 均有终态及证据；登记或外部知识能力不可用时可以记录 `skipped`、`failed` 或 `local_only`，不能留空。重复执行已完成的 Close 保持幂等。

## 校验

每个阶段交付前执行：

```powershell
python <state-script> validate --task-dir docs/[任务目录]
```

若机器状态与 `status.md` 投影不一致，先定位并用状态命令修复；不要通过手工编辑两份状态掩盖问题。AI 登记只负责 session 到任务的跨会话索引，不能替代任务状态文件。
