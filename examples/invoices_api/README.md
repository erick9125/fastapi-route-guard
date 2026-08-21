# Invoices API example

A tiny FastAPI app that uses FastAPI Route Guard for resource-level
authorization. Authentication is a demo `X-User` header, not a real identity
provider.

```bash
uv sync --group dev
uv run uvicorn examples.invoices_api.app:app --reload
```

Try:

```bash
curl -H "X-User: user-a" http://127.0.0.1:8000/invoices/invoice-a
curl -H "X-User: user-a" http://127.0.0.1:8000/invoices/invoice-b
```

The first call returns `200`. The second is an ID swap into tenant B and
returns `403`.
