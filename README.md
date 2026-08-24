# z-claude-plugins

> 个人 Claude 插件仓库（marketplace），模型参考 [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community)。

一个 **monorepo 形式的插件市场**：仓库根目录用 `.claude-plugin/marketplace.json` 描述市场，
每个插件放在各自的子目录里（如 `feishu-notify/`），各自带 `.claude-plugin/plugin.json`。
新增插件只需往 `plugins` 列表里加一条，互不干扰。

## 已收录插件

| 插件 | 说明 | 分类 |
| --- | --- | --- |
| [`feishu-notify`](./feishu-notify) | Claude 触发 hook 时通过飞书自建应用推送私聊卡片通知 | productivity |

## 安装使用

### 1. 添加市场

在 Claude Code / Cowork 中：

```
/plugin marketplace add https://github.com/zengsipei/z-claude-plugins
```

市场名取自 `marketplace.json` 的 `name` 字段：`z-claude-plugins`。

### 2. 安装插件

```
/plugin install feishu-notify@z-claude-plugins
```

### 3. 本地调试（不发布也能用）

直接以插件目录加载，仅当前会话生效：

```bash
claude --plugin-dir ./feishu-notify
```

改完内容后在 Claude Code 里 `/plugin` 重载即可。

## 如何新增一个插件

1. 复制模板：`cp -r _template my-plugin`，重命名为你的插件目录。
2. 编辑 `my-plugin/.claude-plugin/plugin.json`：`name` / `version` / `description` / `author` / `repository` / `license` / `keywords`。
3. 把功能放进去：
   - **hook 类** → `my-plugin/hooks/`，并在 `my-plugin/hooks/hooks.json` 注册。
   - **slash command** → `my-plugin/commands/<name>.md`。
   - **skill** → `my-plugin/skills/<name>/SKILL.md`。
   - **自定义 agent** → `my-plugin/agents/<name>.md`。
4. 在根 `.claude-plugin/marketplace.json` 的 `plugins` 数组追加一条：

   ```json
   {
     "name": "my-plugin",
     "source": "./my-plugin",
     "description": "一句话说明",
     "category": "productivity"
   }
   ```
5. 提交：`git add . && git commit -m "feat: add my-plugin" && git push`。

> 注意：只有写进 `marketplace.json` 的插件才会被市场暴露；`_template/` 仅作脚手架，不会被安装。

## 目录结构

```
z-claude-plugins/
├── .claude-plugin/
│   └── marketplace.json        # 市场清单（name + plugins 列表）
├── feishu-notify/              # 插件 1
│   ├── .claude-plugin/
│   │   └── plugin.json         # 插件清单
│   ├── hooks/                  # _hook 脚本 + hooks.json 注册
│   ├── skills/                 # skills（<name>/SKILL.md）
│   ├── commands/               # slash commands（平面 md）
│   ├── docs/                   # ADR / agents / research
│   ├── CLAUDE.md               # 插件级工程配置入口
│   └── README.md               # 插件说明
├── _template/                  # 新插件脚手架（不安装）
├── LICENSE
└── README.md                   # 本文件
```

## 说明

- 本仓库由原本的单插件仓库重构为市场结构（monorepo），安装方式见上方「安装使用」。
- 远程仓库名与本地目录一致，均为 `z-claude-plugins`；安装 URL 用仓库地址，市场后缀来自 `marketplace.json` 的 `name`。
- 含密钥文件（如 `feishu-notify/hooks/feishu_config.json`）已 gitignore，切勿提交。
