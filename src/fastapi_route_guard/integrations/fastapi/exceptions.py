from fastapi import HTTPException

from fastapi_route_guard.core.result import AuthorizationResult


class AuthorizationDenied(HTTPException):
    def __init__(self, result: AuthorizationResult | None = None) -> None:
        super().__init__(status_code=403, detail="Forbidden")
        self.result = result
