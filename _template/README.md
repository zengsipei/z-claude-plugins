# my-plugin

> 这是一个**插件脚手架**。复制它、改个名、填好配置，你就有一个新插件的起点。

```
cp -r _template my-plugin ─▶ 填 plugin.json ─▶ 加进 marketplace.json ─▶ 上架完成
```

## 怎么用它造一个新插件
1. 复制目录：`cp -r _template my-plugin`，把 `my-plugin` 改成你的名字。
2. 填 `my-plugin/.claude-plugin/plugin.json`（名字、版本、描述等）。
3. 在根 `marketplace.json` 的 `plugins` 里加一条，让市场能发现它。

## 这个模板带了哪些空目录
- `hooks/` —— hook 脚本（注册见 `hooks/hooks.json`）
- `skills/` —— skills（`<名字>/SKILL.md`）
- `commands/` —— 命令（平面 `.md`）

> 可选：`agents/`（自定义 agent）按需自建，模板未预置。

## 装好后的安装命令
```
/plugin marketplace add https://github.com/zengsipei/z-claude-plugins
/plugin install my-plugin@z-claude-plugins
```
> 记得先把 `my-plugin` 加进根 `marketplace.json`，否则上面这行会找不到它。

## 功能
TODO：用一句话写清楚这个插件提供什么能力。
