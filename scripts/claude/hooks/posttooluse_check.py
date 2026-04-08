#!/usr/bin/env python3
"""PostToolUse hook: syntax check for .py / .json / .yaml files after Edit or Write."""
import json
import py_compile
import sys


def _load() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _check_python(path: str) -> str | None:
    try:
        py_compile.compile(path, doraise=True)
        return None
    except py_compile.PyCompileError as e:
        return str(e)


def _check_json(path: str) -> str | None:
    try:
        with open(path) as f:
            json.load(f)
        return None
    except json.JSONDecodeError as e:
        return str(e)


def _check_yaml(path: str) -> str | None:
    try:
        import yaml  # noqa: PLC0415 — optional dependency
    except ImportError:
        return None  # pyyaml 未インストール時はスキップ
    try:
        with open(path) as f:
            yaml.safe_load(f)
        return None
    except yaml.YAMLError as e:
        return str(e)


def main() -> None:
    data = _load()
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or ""
    if not path:
        sys.exit(0)

    try:
        if path.endswith(".py"):
            error = _check_python(path)
        elif path.endswith(".json"):
            error = _check_json(path)
        elif path.endswith((".yaml", ".yml")):
            error = _check_yaml(path)
        else:
            sys.exit(0)
    except OSError:
        # ファイルが存在しない・読み取り不可の場合はサイレントにスキップ
        sys.exit(0)

    if error:
        print(f"[posttooluse] syntax error in {path}:\n{error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
