from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIRS = ["apps", "services", "packages", "tests"]


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for directory in SEARCH_DIRS:
        path = ROOT / directory
        if not path.exists():
            continue
        files.extend(sorted(path.rglob("*.py")))
    return files


def main() -> None:
    files = iter_python_files()
    failures: list[tuple[Path, str]] = []

    for file_path in files:
        try:
            ast.parse(file_path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            failures.append((file_path, f"{exc.msg} (line {exc.lineno})"))

    if failures:
        for file_path, message in failures:
            print(f"FAIL {file_path}: {message}")
        raise SystemExit(1)

    print(f"syntax_ok files={len(files)}")


if __name__ == "__main__":
    main()
