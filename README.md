# z-claude-plugins

> 一句话：这是你自己的「Claude 插件商店」。装好这个市场，就能一键安装里面的小工具。

这是一个 **插件市场仓库（monorepo）**，像一家小商店：

```
这个仓库 = 商店
  ├── 货架：.claude-plugin/marketplace.json（列出所有插件）
  └── 商品：每个子目录一个插件，自带配置和说明，互不干扰
```

装它只要两步：把商店加进 Claude，再从货架装走插件（见下）。
加新插件也一样简单：复制 `_template`、填好配置、在 `marketplace.json` 里加一条。

## 里面有什么

| 插件 | 干嘛用 | 分类 |
| --- | --- | --- |
| [`feishu-notify`](./feishu-notify) | Claude 干活时，通过飞书给你发通知卡片 | productivity |
| [`dsh-spec`](./dsh-spec) | 给项目做活文档 + 变更台账 + 评审闸门，防代码腐化 | engineering |
| [`sdlc`](./sdlc) | 把软件开发生命周期纪律搬进 Claude Code：文档先行、grill 定稿、阶段门禁、跨会话续接 | engineering |

## 怎么用（两步）

### 1. 添加这个市场
在 Claude Code / Cowork 里运行：
```
/plugin marketplace add https://github.com/zengsipei/z-claude-plugins
```

### 2. 安装插件
```
/plugin install feishu-notify@z-claude-plugins
/plugin install dsh-spec@z-claude-plugins
/plugin install sdlc@z-claude-plugins
```

### 想本地先试（不发布也能用）
直接以目录加载，仅当前会话生效：
```bash
claude --plugin-dir ./feishu-notify
```
改完内容后在 Claude Code 里 `/plugin` 重载即可。

## 怎么加一个新插件
1. 复制模板：`cp -r _template my-plugin`，重命名目录。
2. 填 `my-plugin/.claude-plugin/plugin.json` 的 `name` / `version` / `description` 等。
3. 放功能：
   - **hook** → `my-plugin/hooks/`，并在 `hooks/hooks.json` 注册。
   - **命令** → `my-plugin/commands/<名字>.md`。
   - **skill** → `my-plugin/skills/<名字>/SKILL.md`。
   - **agent** → `my-plugin/agents/<名字>.md`。
4. 在根 `marketplace.json` 的 `plugins` 里加一条：
   ```json
   { "name": "my-plugin", "source": "./my-plugin", "description": "一句话说明", "category": "productivity" }
   ```
5. 提交并推送：`git add . && git commit -m "feat: add my-plugin" && git push`。

> ⚠️ 只有写进 `marketplace.json` 的插件才会被市场暴露；`_template/` 只是脚手架，不会被安装。

## 目录结构

```
z-claude-plugins/
├── .claude-plugin/marketplace.json   # 市场清单（name + plugins 列表）
├── feishu-notify/                    # 插件 1
├── dsh-spec/                         # 插件 2
├── sdlc/                             # 插件 3
├── _template/                        # 新插件脚手架（不安装）
├── LICENSE
└── README.md                         # 本文件
```

## 说明
- 本仓库由单插件仓库重构为市场结构（monorepo）。
- 安装 URL 用仓库地址，市场后缀来自 `marketplace.json` 的 `name`。
- 含密钥的文件（如 `feishu-notify/hooks/feishu_config.json`）已 gitignore，切勿提交。
