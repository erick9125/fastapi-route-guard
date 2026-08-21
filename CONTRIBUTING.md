# Contributing

Thanks for contributing to FastAPI Route Guard.

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest --cov
uv build
```

## Guidelines

- Keep `src/fastapi_route_guard/core`, `evaluators`, `registry`, and `testing`
  independent of FastAPI, Starlette, and `HTTPException`.
- Do not authenticate users in this library.
- Fail closed: unknown handlers, unknown resources, and thrown resolvers must
  not allow access.
- Do not put internal reason codes, tenant ids, or owner ids in HTTP bodies.
- Add unit, integration, or security tests for behavioral changes.

## Pull requests

1. Keep the change scoped.
2. Update docs when public API behavior changes.
3. Ensure `ruff`, `mypy`, and `pytest --cov` pass.
