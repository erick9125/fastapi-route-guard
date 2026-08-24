# Contributing

Thanks for contributing to FastAPI Route Guard.

## Development

```bash
uv sync --locked --group dev
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest --cov
uv build
```

`uv.lock` is tracked so CI resolves the same development dependencies every
run; `--locked` fails instead of silently relocking. Run `uv lock` after
changing dependencies or the project version, and commit the result. The lock
does not constrain what consumers install — `dependencies` in `pyproject.toml`
stays deliberately loose.

Before a release, check that the built wheel works on its own:

```bash
uv build
uvx twine check --strict dist/*
uv venv --no-project .wheelcheck
uv pip install --python .wheelcheck/bin/python dist/*.whl
cd .wheelcheck && ./bin/python -c "import fastapi_route_guard as g; print(g.__version__)"
```

## Guidelines

- Keep `src/fastapi_route_guard/core`, `evaluators`, `registry`, and `testing`
  independent of FastAPI and Starlette. `integrations/` is the only place the
  framework belongs, and `tests/unit/test_engine_isolation.py` enforces it.
- Let FastAPI resolve dependencies. The guard binds the resource id and the
  loaded object; everything else is exposed as a real FastAPI dependency so
  `yield` teardown, `dependency_overrides`, and the per-request cache keep
  working.
- Do not authenticate users in this library.
- Fail closed: unknown handlers, unknown resources, and thrown resolvers must
  not allow access.
- Do not put internal reason codes, tenant ids, or owner ids in HTTP bodies.
- Add unit, integration, or security tests for behavioral changes.

## Pull requests

1. Keep the change scoped.
2. Update docs when public API behavior changes.
3. Ensure `ruff`, `mypy`, and `pytest --cov` pass.
