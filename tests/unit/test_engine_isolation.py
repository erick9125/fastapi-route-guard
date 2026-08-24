import ast
from pathlib import Path

ENGINE_ROOTS = (
    "src/fastapi_route_guard/core",
    "src/fastapi_route_guard/evaluators",
    "src/fastapi_route_guard/registry",
    "src/fastapi_route_guard/testing",
    "src/fastapi_route_guard/exceptions.py",
)
FORBIDDEN_ROOTS = frozenset({"fastapi", "starlette"})


def _engine_files() -> list[Path]:
    root = Path(__file__).resolve().parents[2]
    files: list[Path] = []
    for relative in ENGINE_ROOTS:
        path = root / relative
        if path.is_file():
            files.append(path)
        else:
            files.extend(path.rglob("*.py"))
    return files


def _imported_roots(source: str) -> set[str]:
    """Top-level package of every import, read from the AST.

    Matching import statements as text made the check trip over comments and
    docstrings, and miss aliased imports.
    """
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_the_engine_is_collected() -> None:
    assert _engine_files()


def test_core_engine_does_not_import_a_web_framework() -> None:
    """The evaluator must stay testable without FastAPI.

    The integration layer under `integrations/` is where the framework lives.
    """
    for file in _engine_files():
        imported = _imported_roots(file.read_text(encoding="utf-8"))
        leaked = imported & FORBIDDEN_ROOTS
        assert not leaked, f"{file.name} imports {sorted(leaked)}"


def test_the_integration_layer_is_the_only_framework_boundary() -> None:
    root = Path(__file__).resolve().parents[2] / "src/fastapi_route_guard"
    for file in root.rglob("*.py"):
        if "integrations" in file.parts or file.name == "__init__.py":
            continue
        imported = _imported_roots(file.read_text(encoding="utf-8"))
        assert not imported & FORBIDDEN_ROOTS, file
