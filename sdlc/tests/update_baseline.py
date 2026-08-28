#!/usr/bin/env python3
"""重生成内核字节基准 `kernel-baseline.json`。

快照纪律（见仓库根 `docs/adr/0001-快照移植纪律.md`）：`skills/sdlc/` 是上游
快照，内核字节级原样，只有「表面适配」层可按本仓库惯例改写。本脚本为每个
快照文件记下 sha256 与类别，供 `test_snapshot_contract.py` 的 `KernelFrozenTest`
比对。

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

UPSTREAM = "AtlantisYuki/prompt@7cdfc64588a1a8eb7d338e3f6f717f1c7abcd81"

# 移植时做过表面适配的文件（相对 skills/sdlc/）：允许再改，但改了要能说明理由。
# 其余一律是内核：与上游字节级一致，动一个字节就要走整体重快照。
ADAPTED = {
    "SKILL.md",
    "references/registration.md",
}

# 编译产物不进快照核对。
SKIP_SUFFIXES = (".pyc",)
SKIP_DIRS = {"__pycache__"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect() -> dict[str, dict[str, str]]:
    files: dict[str, dict[str, str]] = {}
    for path in sorted(SNAPSHOT.rglob("*")):
        if not path.is_file() or path.suffix in SKIP_SUFFIXES:
            continue
        if SKIP_DIRS & set(path.relative_to(SNAPSHOT).parts):
            continue
        rel = path.relative_to(SNAPSHOT).as_posix()
        files[rel] = {
            "sha256": sha256(path),
            "category": "adapted" if rel in ADAPTED else "kernel",
        }
    return files


def main() -> int:
    if not SNAPSHOT.is_dir():
        raise SystemExit(f"找不到快照目录：{SNAPSHOT}")
    files = collect()
    missing = ADAPTED - set(files)
    if missing:
        raise SystemExit(f"ADAPTED 里列出的文件在快照中不存在：{sorted(missing)}")

    baseline = {
        "upstream": UPSTREAM,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
