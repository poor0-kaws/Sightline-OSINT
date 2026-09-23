"""Mechanical checks for the backend dependency policy.

These tests parse the import graph with ``ast``; they prove only the file edges
they read. They do not prove that components own the right responsibility.
"""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"


def _module_name(py_file: Path) -> str:
    """Return the dotted module name for one backend file."""
    relative = py_file.relative_to(BACKEND_ROOT.parent)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _backend_modules() -> dict[str, Path]:
    """Return every backend module name mapped to its file path."""
    return {_module_name(path): path for path in BACKEND_ROOT.rglob("*.py")}


def _backend_imports(py_file: Path) -> set[str]:
    """Return the backend module names one file imports."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("backend"):
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("backend"):
                    imported.add(alias.name)
    return imported


def _resolve_import(imported: str, modules: dict[str, Path]) -> str | None:
    """Resolve an import string to the longest existing backend module."""
    candidate = imported
    while candidate:
        if candidate in modules:
            return candidate
        if "." not in candidate:
            return None
        candidate = candidate.rsplit(".", 1)[0]
    return None


def _dependency_graph() -> dict[str, set[str]]:
    """Return module -> internal backend dependencies."""
    modules = _backend_modules()
    graph: dict[str, set[str]] = {name: set() for name in modules}
    for name, path in modules.items():
        for imported in _backend_imports(path):
            resolved = _resolve_import(imported, modules)
            if resolved is not None and resolved != name:
                graph[name].add(resolved)
    return graph


def test_utils_is_a_leaf_package() -> None:
    """backend.utils must not import any other backend package."""
    modules = _backend_modules()
    for name, path in modules.items():
        if not name.startswith("backend.utils"):
            continue

        for imported in _backend_imports(path):
            assert imported.startswith("backend.utils"), (
                f"{name} must stay a leaf but imports {imported}"
            )


def test_backend_import_graph_has_no_cycles() -> None:
    """The backend import graph must stay acyclic."""
    graph = _dependency_graph()
    color: dict[str, int] = {name: 0 for name in graph}
    stack: list[str] = []

    def visit(node: str) -> None:
        color[node] = 1
        stack.append(node)
        for dependency in sorted(graph.get(node, ())):
            if color[dependency] == 1:
                cycle_start = stack.index(dependency)
                cycle = stack[cycle_start:] + [dependency]
                raise AssertionError("Import cycle: " + " -> ".join(cycle))
            if color[dependency] == 0:
                visit(dependency)
        stack.pop()
        color[node] = 2

    for module in sorted(graph):
        if color[module] == 0:
            visit(module)
