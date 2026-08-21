from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RoutePolicy:
    resource: str | None = None
    action: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    scopes: frozenset[str] = field(default_factory=frozenset)
    ownership: bool = False
    tenant: bool = False
    handlers: tuple[str, ...] = ()
