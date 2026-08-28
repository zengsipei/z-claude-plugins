"""全仓统一测试入口。

三个插件的测试目录都不是包，`python -m unittest discover` 从仓库根跑会得到
**0 个测试**（Python 3.13 的 discover 不再支持命名空间包；先插 sys.path 也没用）。
所以逐目录 discover，每个目录的 top_level_dir 指自己。

跑法：
    python tools/run_tests.py          全部四个目录
    python tools/run_tests.py sdlc/tests tools   指定目录（相对仓库根）

失败退出码非零，便于接 CI。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ("sdlc/tests", "dsh-spec/hooks", "feishu-notify/hooks", "tools")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    dirs = [ROOT / a for a in argv] if argv else [ROOT / t for t in TARGETS]

    missing = [str(d) for d in dirs if not d.is_dir()]
    if missing:
        print("目录不存在：%s" % ", ".join(missing))
        return 2

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for d in dirs:
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))
        suite.addTests(
            loader.discover(str(d), pattern="test_*.py", top_level_dir=str(d))
        )

    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
