from pathlib import Path

ENGINE_ROOTS = (
    "src/fastapi_route_guard/core",
    "src/fastapi_route_guard/evaluators",
    "src/fastapi_route_guard/registry",
    "src/fastapi_route_guard/testing",
    "src/fastapi_route_guard/exceptions.py",
)


def test_core_engine_does_not_import_fastapi() -> None:
    root = Path(__file__).resolve().parents[2]
    files: list[Path] = []
    for relative in ENGINE_ROOTS:
        path = root / relative
        if path.is_file():
            files.append(path)
        else:
            files.extend(path.rglob("*.py"))
    assert files
    for file in files:
        text = file.read_text(encoding="utf-8")
        assert "from fastapi import" not in text
        assert "from fastapi." not in text
        assert "import fastapi\n" not in text
        assert "HTTPException" not in text
        assert "starlette" not in text
