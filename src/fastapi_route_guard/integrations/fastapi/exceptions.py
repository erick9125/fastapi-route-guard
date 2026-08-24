from fastapi import HTTPException

from fastapi_route_guard.core.result import AuthorizationResult


class AuthorizationDenied(HTTPException):
    """HTTP 403 for a denied request.

    The body stays generic on purpose: violation codes, tenant ids, and owner
    ids must not reach the caller. `result` carries them in-process — for tests,
    logging, or an exception handler — and is never serialized.

    Register a handler for this exception to shape the response:

        @app.exception_handler(AuthorizationDenied)
        async def on_denied(request, exc): ...
    """

    def __init__(
        self,
        result: AuthorizationResult | None = None,
        *,
        detail: str = "Forbidden",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=403, detail=detail, headers=headers)
        self.result = result
