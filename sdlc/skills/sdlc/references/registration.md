# AI 登记与历史查询

登记用于跨会话、跨工具和跨仓库视角续接，不代替 `onlyAI/task-state.json`、`status.md`、设计文档和施工记录。核心脚本：`scripts/ai_register_core.py`。

用户批准进入 SDLC 时，允许按本协议维护 AI 登记后端；这项流程授权仅覆盖登记数据，不包含业务数据库查询、写入、迁移或生产执行。业务数据操作始终遵循单独授权门禁。

## 目录

- [必备字段](#必备字段)
- [后端选择](#后端选择)
- [身份规则](#身份规则)
- [Hook 安装](#hook-安装)
- [登记身份](#登记身份)
- [回填进度](#回填进度)
- [历史查询](#历史查询)

## 必备字段

每个 session 行至少维护：

- `session_id`：可信 hook 注入的会话标识，唯一主键；
- `task_dir`：规范化后的 `docs/[需求目录]/`；
- `tool`、`model`：当前 AI 工具和模型；
- `branch`：当前 Git 分支；
- `completed_tasks`：已完成任务 JSON 列表，追加时去重；
- `progress`：当前完成进度。

兼容字段包括工作目录、来源、续接命令和更新时间。旧 `feature` 字段只作为历史兼容别名，新流程统一写 `completed_tasks`。

## 后端选择

1. 如果显式传入 `--db`，只使用指定 SQLite。
2. 否则读取 Git 根目录 `docs/ai-register.json`，按 `backend` 使用 `postgresql` 或 `mysql`。
3. 配置文件不存在、格式无效、驱动未安装、连接失败或远程操作失败时，输出降级原因并使用 Git 根目录 `docs/ai-register.db`。
4. 每次命令把实际后端输出为 `backend=postgresql`、`backend=mysql` 或 `backend=sqlite`，将该结果写入 `status.md` 或操作记录。

从 `assets/ai-register.config.example.json` 复制配置到项目 `docs/ai-register.json`。密码字段直接写在 JSON 的 `password` 中，由登记脚本读取：

```json
{
  "backend": "postgresql",
  "host": "127.0.0.1",
  "port": 5432,
  "database": "ai_register",
  "user": "ai_register",
  "password": "change-me",
  "connect_timeout": 3,
  "sslmode": "prefer"
}
```

使用 MySQL 时把 `backend` 改为 `mysql`、端口改为 `3306`，移除 `sslmode`。PostgreSQL 驱动支持 `psycopg` / `psycopg2`，MySQL 驱动支持 `pymysql` / `mysql-connector-python`；驱动不是 Skill 的强制依赖，缺失时自动使用 SQLite。

实际 `docs/ai-register.json` 含连接密码，应加入项目忽略规则，不提交到版本库。远程后端短暂不可用时可能产生 SQLite 降级记录；查询命令会明确当前读取的后端，不把两个来源伪装为已自动合并。

## 身份规则

可信 sessionId 来源（同级，任取其一即可登记）：

1. **SessionStart hook 注入**：对话上下文或 hook 输出中的 session id（含环境变量如 `GROK_SESSION_ID`）。
2. **协议约定的上下文文件**：hook 写出的身份文件中的 session id，例如工作区 `.grok/sdlc-session-context.txt` 或 `~/.grok/sdlc-session-context.txt`。

约束：

- SessionStart hook 只注入身份上下文（及必要时写上述约定文件），**不写** AI 登记库。
- AI 只使用上述可信来源中的 sessionId；hook 注入与约定上下文文件**同级可信**，不得互相排斥。
- 没有可信 sessionId 时跳过登记并在 `status.md` 记录原因；不得扫描 transcript 修改时间或“最新会话”猜测身份。
- `branch` 未显式传入时由脚本从 Git 读取；无法识别时保留原值，不伪造分支。

## Hook 安装

- Claude Code：作为插件安装时，SessionStart hook 由插件 `hooks/hooks.json` 自动接线，无需任何安装步骤
- Codex：`scripts/install_codex_hook.ps1` 仅随快照留存作参考，勿用
- Grok：`scripts/install_grok_hook.ps1` 仅随快照留存作参考，勿用

Grok 的 SessionStart 在原生文档中为被动 hook（stdout 不一定注入对话）。安装后的 Grok hook 会：

1. 优先读取 `GROK_SESSION_ID` / `GROK_WORKSPACE_ROOT`（stdin JSON 仅补缺）；
2. 写出 `.grok/sdlc-session-context.txt` 与 `~/.grok/sdlc-session-context.txt` 作为可信身份兜底；
3. 仍输出 Claude 兼容的 `hookSpecificOutput.additionalContext`，供兼容层使用。

登记前若对话上下文未见 session id，可读取上述上下文文件；仍不可得则跳过登记。

## 登记身份

```bash
python <skill>/scripts/ai_register_core.py upsert \
  --session <sessionId> --tool "Codex" --model <model> \
  --cwd <repo-or-session-cwd> --branch <branch>
```

Claude Code 将 `--tool` 改为 `Claude Code`；Grok 将 `--tool` 改为 `Grok`。重复 upsert 使用非空值更新身份，不用空值擦除已有记录。

## 回填进度

```bash
python <skill>/scripts/ai_register_core.py progress \
  --session <sessionId> --task-dir "docs/[需求目录]/" \
  --completed-task "T-01：[已完成任务]" \
  --completed-task "T-02：[已完成任务]" \
  --progress "75%" --cwd <repo-or-session-cwd>
```

`--completed-task` 可以重复传入，脚本与已有任务合并去重。阶段切换、grill 闭环、施工任务完成、测试、阻塞和回退时，在任务状态脚本成功提交后同频更新登记。

已完成任务从当前工作流主文档提取：Standard 读取 `002-施工文档.md`，Debug 读取 `Debug排查记录.md` 的排查/修复结论，Script 读取 `脚本任务.md` 的执行结论。不要为了登记给专项流程补建标准施工文档。

`sdlc-close` 使用 `close` 子命令完成最终同步；省略 `--progress` 时默认为 `100%`：

```bash
python <skill>/scripts/ai_register_core.py close \
  --session <sessionId> --task-dir "docs/[需求目录]/" \
  --completed-task "T-01：[已完成任务]" --cwd <repo-or-session-cwd>
```

## 历史查询

```bash
python <skill>/scripts/ai_register_core.py query
python <skill>/scripts/ai_register_core.py query --task-dir "docs/[需求目录]/"
python <skill>/scripts/ai_register_core.py query --keyword "[任务、分支或会话关键词]"
```

`sdlc-history` 只查询当前实际可用后端，不创建设计、施工或测试文档。输出 session、目录、工具、模型、分支、已完成任务、进度和续接命令；无结果时明确说明后端和匹配条件。
