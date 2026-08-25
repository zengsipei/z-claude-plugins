#!/usr/bin/env python3
"""dsh-spec 评审/预推闸门占位实现。

⚠️ 行为尚未定型：D3 (#18) 仍在开放中，决定闸门是 Stop 层还是 PreToolUse 层、
是否硬阻断「无 note 不合并」、失败时的提醒 vs 阻断语义。本文件为 no-op 占位，
安装后不会阻断任何流程，仅在 stderr 打印提示。

D3 关闭后，由对应 ticket 替换本文件为真正的闸门逻辑。
"""
import sys


def main() -> int:
    sys.stderr.write(
        "[dsh-spec-gate] 占位中：闸门行为待 D3 (#18) 决定，当前 no-op 不阻断。\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
