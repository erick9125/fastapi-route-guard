from typing import Any

from starlette.requests import Request


def build_request_context(request: Request) -> dict[str, Any]:
    return {
        "method": request.method,
        "path": request.url.path,
        "path_params": dict(request.path_params),
    }
