# my-plugin

> 插件脚手架模板。复制本目录、改名、填好 `.claude-plugin/plugin.json`，
> 并在根 `.claude-plugin/marketplace.json` 的 `plugins` 数组里登记即可。

## 功能

TODO：描述这个插件提供什么能力。

## 包含的目录

- `hooks/` —— hook 脚本，注册见 `hooks/hooks.json`
- `skills/` —— skills（`<name>/SKILL.md`）
- `commands/` —— slash commands（平面 `.md`）
- `agents/` —— 自定义 agent 定义（可选）

## 安装

```
/plugin marketplace add https://github.com/zengsipei/z-claude-plugins
/plugin install my-plugin@z-claude-plugins
```
