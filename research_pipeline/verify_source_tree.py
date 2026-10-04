#!/usr/bin/env python3
"""Compile and audit the tracked canonical source bundle."""
from __future__ import annotations

import ast
from pathlib import Path
import py_compile


ROOT = Path(__file__).resolve().parent


def main() -> None:
    python_files = sorted(ROOT.rglob("*.py"))
    violations: list[str] = []
    for path in python_files:
        py_compile.compile(str(path), doraise=True)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            text = node.value.replace("\\", "/")
            if "DB/japan-" in text and "/pipeline" in text:
                violations.append(f"{path.relative_to(ROOT)}: {node.value}")
    if violations:
        raise RuntimeError(
            "Historical DB pipeline dependencies found:\n" + "\n".join(violations)
        )
    print(f"PASS: {len(python_files)} canonical Python sources compiled and audited")


if __name__ == "__main__":
    main()
