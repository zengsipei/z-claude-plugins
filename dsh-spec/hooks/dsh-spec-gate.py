#!/usr/bin/env python3
"""dsh-spec 评审/预推「提醒闸门」（warn-only Stop hook）。

落地 D3 (#18) 的「分层双闸」中的提醒闸口：agent 即将结束一轮回复（Stop）
时，若工作树存在未留账改动，则向 stderr 打一条**非阻断**提醒。

严格「有账」语义（#43）：只有以「存在/新增」形态出现的 note/ADR 路径才算
留账——A/M/C 状态、rename 目标端、`??` 未跟踪；仅删除（D）一条 note 或
仅把 note rename 挪走都不算「有账」，仍会提醒。

设计约束（D3 #18 / R2 #14 / #43）：
- 绝不阻断：任何情况下都返回退出码 0（含异常、非 git 仓库、无 python 等）。
- 不做 PreToolUse 硬阻断（违反 build 层禁令）；硬阻断归人触发的
  `/dsh-spec-review --gate strict` 命令。
- 仅做会话级粗检查；逐 commit↔note 精确匹配归 `/dsh-spec-review` 命令。
- 不调用外部 skill（code-review / tdd）；测试不变量轴留 v2。
- 仅对已「采纳」dsh-spec 的仓库提醒（存在 `.agents/notes`、`.agents/RULES.md`、
  `.agents/LEDGER.md` 任一），避免打扰未使用该台账的仓库。
- 决策纯函数化：`should_warn` 一次判定完「是否采纳」与「是否有账」——
  porcelain 行解析（XY 状态码、rename 源/目标端拆分）与采纳判定全部藏在其内，
  零 IO、零 subprocess；`main()` 只负责 IO 编排（探测标记、跑 git status）。
"""
import os
import subprocess
import sys

NOTE_PREFIXES = (".agents/notes/", "docs/adr/")
# 两组常量的唯一声明处是 RULES.md「附：脚手架清单」，由 hooks/test_dsh_spec_gate.py 一致性测试执法。
ADOPT_MARKERS = (".agents/notes", ".agents/RULES.md", ".agents/LEDGER.md")

WARNING = (
    "[dsh-spec] 提醒：本轮工作树有未留账的改动"
    "（注意：仅删除或挪走 note/ADR 不算留账）。\n"
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


def _is_note(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in NOTE_PREFIXES)


def should_warn(status_lines, existing_markers) -> bool:
    """纯决策：给定 porcelain 行与仓库里实际存在的采纳标记，判定是否打提醒。

    existing_markers 为空即未采纳，静默放行。

    严格「有账」语义：A/M/C、rename 目标端、`??` 未跟踪的 note/ADR 路径算
    留账；仅 D（删除）与仅 rename 源端（账被挪走）不算。
    """
    if not existing_markers:
        return False
    has_changes = False
    has_note = False
    for line in status_lines:
        if len(line) < 4:  # 至少 "XY path"；空行/残行直接忽略。
            continue
        xy, rest = line[:2], line[3:]
        has_changes = True
        # rename/copy 行形如 "XY orig -> new"：源端已被挪走，只看目标端。
        path = rest.split(" -> ", 1)[1] if " -> " in rest else rest
        if _is_note(path) and (xy[0] in "AMCR?" or xy[1] in "AMCR"):
            has_note = True
    return has_changes and not has_note


def main() -> int:
    try:
        # 消费 hook 输入（Claude Code 经 stdin 传入 JSON），丢弃即可。
        try:
            sys.stdin.read()
        except Exception:
            pass

        cwd = os.getcwd()
        root = find_repo_root(cwd)
        if root is None:
            return 0  # 非 git 仓库：静默放行。
        existing = [m for m in ADOPT_MARKERS if os.path.exists(os.path.join(root, m))]
        if not existing:
            # 性能短路，不是第二条规则：未采纳的仓库不必为一个注定静默的结果付
            # git status 的代价（-uall 会遍历全部未跟踪文件，大仓上可达秒级）。
            # 「未采纳即静默」这条规则只声明在 should_warn 里，并由其测试守住。
            return 0

        proc = subprocess.run(
            ["git", "-C", root, "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, timeout=4,
        )
        if proc.returncode != 0:
            return 0  # 无法读取状态：放行，不阻断。

        if should_warn(proc.stdout.splitlines(), existing):
            sys.stderr.write(WARNING)
        return 0
    except Exception:
        return 0  # 任何异常都不阻断流程。


if __name__ == "__main__":
    sys.exit(main())
