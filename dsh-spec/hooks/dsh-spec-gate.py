#!/usr/bin/env python3
"""dsh-spec 评审/预推「提醒闸门」（warn-only Stop hook）。

落地 D3 (#18) 的「分层双闸」中的提醒闸口：agent 即将结束一轮回复（Stop）
时，若工作树存在未提交改动、且这批改动里没有任何 `.agents/notes/` 或
`docs/adr/` 文件，则向 stderr 打印一条**非阻断**提醒，提示先写 note/ADR。

设计约束（D3 #18 / R2 #14）：
- 绝不阻断：任何情况下都返回退出码 0（含异常、非 git 仓库、无 python 等）。
- 不做 PreToolUse 硬阻断（违反 build 层禁令）；硬阻断归人触发的
  `/dsh-spec-review --gate strict` 命令。
- 仅做会话级粗检查；逐 commit↔note 精确匹配归 `/dsh-spec-review` 命令。
- 不调用外部 skill（code-review / tdd）；测试不变量轴留 v2。
- 仅对已「采纳」dsh-spec 的仓库提醒（存在 `.agents/notes/` 或 `docs/adr/`
  或根 `SPEC.md`/`ARCHITECTURE.md`），避免打扰未使用该台账的仓库。
"""
import os
import subprocess
import sys

NOTE_PREFIXES = (".agents/notes/", "docs/adr/")
# 采纳判定标记：取自 RULES.md「附：脚手架清单」（当前为其中四项子集）。
# 改脚手架清单须同步评估此常量；改此常量须同步 RULES.md 附录，反之亦然。
ADOPT_MARKERS = (".agents/notes", "docs/adr", "SPEC.md", "ARCHITECTURE.md")

WARNING = (
    "[dsh-spec] 提醒：本轮工作树有改动，但未建 .agents/notes/ 或 docs/adr/ 记录。\n"
    "  非阻断——合并前请先 /dsh-spec-note 留账，或 /dsh-spec-review --gate strict 审计。\n"
)


def find_repo_root(start: str) -> str | None:
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def is_adopted(root: str) -> bool:
    return any(os.path.exists(os.path.join(root, m)) for m in ADOPT_MARKERS)


def main() -> int:
    try:
        # 消费 hook 输入（Claude Code 经 stdin 传入 JSON），丢弃即可。
        try:
            sys.stdin.read()
        except Exception:
            pass

        cwd = os.getcwd()
        root = find_repo_root(cwd)
        if root is None or not is_adopted(root):
            return 0  # 非 git 仓库或未采纳 dsh-spec：静默放行。

        proc = subprocess.run(
            ["git", "-C", root, "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, timeout=4,
        )
        if proc.returncode != 0:
            return 0  # 无法读取状态：放行，不阻断。
        changes = proc.stdout.splitlines()
        if not changes:
            return 0  # 干净树：假定已带 note 提交或无需改动。

        # 粗检查：改动集是否包含 note/ADR 文件。
        has_note = any(any(p in line for p in NOTE_PREFIXES) for line in changes)
        if not has_note:
            sys.stderr.write(WARNING)
        return 0
    except Exception:
        return 0  # 任何异常都不阻断流程。


if __name__ == "__main__":
    sys.exit(main())
