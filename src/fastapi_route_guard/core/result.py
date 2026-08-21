from dataclasses import dataclass

from fastapi_route_guard.core.violations import ViolationCode


@dataclass(frozen=True, slots=True)
class AuthorizationViolation:
    code: ViolationCode
    message: str


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    allowed: bool
    violations: tuple[AuthorizationViolation, ...] = ()
