"""快照契约测试：守住 sdlc 技能快照的对外行为与跨文件一致性。

测试只测外部行为（CLI 退出码与输出）和跨文件一致性断言，不为可测性
改动快照字节；钩子脚本本体、hooks.json 接线、远程后端路径不在范围内
（规格 Testing Decisions 已裁定）。测试位于插件顶层 `tests/`，不进
`skills/sdlc/` 快照目录——保持快照 1:1 映射可核对。

运行方式：cd sdlc && python -m unittest discover -s tests -v
"""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE / ".." / "skills" / "sdlc" / "scripts"
ASSETS = HERE / ".." / "skills" / "sdlc" / "assets"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


task_state_core = _load_module("task_state_core", SCRIPTS / "task_state_core.py")
ai_register_core = _load_module("ai_register_core", SCRIPTS / "ai_register_core.py")


def _run_cli(module, argv: list[str]) -> tuple[int, str, str]:
    """跑 CLI main()，返回 (退出码, stdout, stderr)。"""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = module.main(argv)
    return code, out.getvalue(), err.getvalue()


class SchemaVersionConsistencyTest(unittest.TestCase):
    """task_state_core.SCHEMA_VERSION ⇔ task-state.schema.json $id。"""

    def test_schema_version_matches_schema_id(self):
        schema = json.loads(
            (ASSETS / "task-state.schema.json").read_text(encoding="utf-8")
        )
        schema_id = schema["$id"]
        self.assertEqual(
            schema_id,
            f"urn:software-dev-process:task-state:v{task_state_core.SCHEMA_VERSION}",
            "SCHEMA_VERSION 与 schema $id 不一致：改任一侧时必须同步另一侧",
        )


class TaskStateCoreCliSmokeTest(unittest.TestCase):
    """18 子命令 CLI 的对外契约：临时目录里 init → show → validate 全链路。"""

    def test_init_show_validate_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = str(Path(tmp) / "docs" / "任务目录")
            code, _, err = _run_cli(
                task_state_core,
                [
                    "init",
                    "--task-dir", task_dir,
                    "--system", "demo-system",
                    "--title", "冒烟任务",
                ],
            )
            self.assertEqual(code, 0, err)

            code, out, err = _run_cli(
                task_state_core, ["show", "--task-dir", task_dir]
            )
            self.assertEqual(code, 0, err)
            state = json.loads(out)
            self.assertEqual(state["schema_version"], task_state_core.SCHEMA_VERSION)
            self.assertEqual(state["system"], "demo-system")

            code, out, err = _run_cli(
                task_state_core, ["validate", "--task-dir", task_dir]
            )
            self.assertEqual(code, 0, err)
            self.assertEqual(out.strip(), "task-state valid")


class AiRegisterCoreSqliteSmokeTest(unittest.TestCase):
    """SQLite 降级路径对外契约：临时目录里 upsert → query 回环。"""

    def test_upsert_then_query_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "ai-register.db")
            code, _, err = _run_cli(
                ai_register_core,
                [
                    "upsert",
                    "--session", "sess-smoke1",
                    "--tool", "zcode",
                    "--branch", "main",
                    "--db", db_path,
                ],
            )
            self.assertEqual(code, 0, err)

            code, out, err = _run_cli(
                ai_register_core,
                ["query", "--keyword", "sess-smoke1", "--db", db_path],
            )
            self.assertEqual(code, 0, err)
            self.assertIn("sess-smoke1", out)


if __name__ == "__main__":
    unittest.main()
