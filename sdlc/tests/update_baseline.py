#!/usr/bin/env python3
"""重生成内核字节基准 `kernel-baseline.json`。

快照纪律（见仓库根 `docs/adr/0001-快照移植纪律.md`，补充与勘误见
`docs/adr/0002-快照身份单一事实源.md`）：`skills/sdlc/` 是上游快照，内核字节级
原样，只有「表面适配」层可按本仓库惯例改写。本脚本为每个快照文件记下 sha256
与类别，供 `test_snapshot_contract.py` 的 `KernelFrozenTest` 比对。

**本脚本不声明任何事实。** 上游提交号与已适配面清单的唯一声明处是
`sdlc/snapshot.json`（三键 `upstream_repo` / `upstream_commit` / `adapted`）；
本脚本只读它、把声明落到基准里。改快照身份请改 `snapshot.json`，再跑本脚本。

何时运行：**重快照之后，且仅在这时**。测试变红有两种可能——有人手贱改了内核
（该修回去），或刚做了重快照（该跑本脚本）。区分不了就别跑。

运行方式：cd sdlc && python tests/update_baseline.py
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAPSHOT = (HERE / ".." / "skills" / "sdlc").resolve()
BASELINE = HERE / "kernel-baseline.json"
IDENTITY = (HERE / ".." / "snapshot.json").resolve()

# 编译产物不进快照核对。
SKIP_SUFFIXES = (".pyc",)
SKIP_DIRS = {"__pycache__"}


def load_identity() -> tuple[str, set[str]]:
    """读唯一声明处 `sdlc/snapshot.json`，返回 (upstream, adapted 集合)。"""
    data = json.loads(IDENTITY.read_text(encoding="utf-8"))
    return (
        "%s@%s" % (data["upstream_repo"], data["upstream_commit"]),
        set(data["adapted"]),
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(adapted: set[str] | None = None) -> dict[str, dict[str, str]]:
    """扫描快照目录。adapted 缺省时读唯一声明处 `snapshot.json`。

    未在 adapted 里的文件一律是内核：与上游字节级一致，动一个字节就要走整体
    重快照。
    """
    if adapted is None:
        adapted = load_identity()[1]
    files: dict[str, dict[str, str]] = {}
    for path in sorted(SNAPSHOT.rglob("*")):
        if not path.is_file() or path.suffix in SKIP_SUFFIXES:
            continue
        if SKIP_DIRS & set(path.relative_to(SNAPSHOT).parts):
            continue
        rel = path.relative_to(SNAPSHOT).as_posix()
        files[rel] = {
            "sha256": sha256(path),
            "category": "adapted" if rel in adapted else "kernel",
        }
    return files


def main() -> int:
    if not SNAPSHOT.is_dir():
        raise SystemExit(f"找不到快照目录：{SNAPSHOT}")
    upstream, adapted = load_identity()
    files = collect(adapted)

    missing = adapted - set(files)
    if missing:
        raise SystemExit(
            f"snapshot.json 的 adapted 里列出的文件在快照中不存在：{sorted(missing)}\n"
            f"两种可能——声明写错，或上游在新提交里删掉了这些文件。\n"
            f"无论哪种都要人看一眼：改 {IDENTITY}，再跑本脚本重生成基准。"
        )

    baseline = {
        "upstream": upstream,
        "files": files,
    }
    BASELINE.write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    kernel = sum(1 for f in files.values() if f["category"] == "kernel")
    print(
        f"已写入 {BASELINE.relative_to(HERE.parent)}："
        f"{len(files)} 个文件（kernel {kernel} / adapted {len(files) - kernel}）"
    )
    print(f"  上游：{upstream}")
    print(
        "  已适配面："
        + ("、".join(sorted(adapted)) if adapted else "（无）")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
