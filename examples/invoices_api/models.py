from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Invoice:
    id: str
    owner_id: str
    tenant_id: str
    status: str
    amount: int


@dataclass(frozen=True, slots=True)
class User:
    id: str
    roles: set[str]
    scopes: set[str]
    tenant_id: str


USERS: dict[str, User] = {
    "user-a": User(
        id="user-a",
        roles=set(),
        scopes={"invoice:read", "invoice:update", "invoice:list"},
        tenant_id="tenant-a",
    ),
    "user-b": User(
        id="user-b",
        roles=set(),
        scopes={"invoice:read", "invoice:update", "invoice:list"},
        tenant_id="tenant-b",
    ),
    "user-c": User(
        id="user-c",
        roles=set(),
        scopes={"invoice:read", "invoice:update"},
        tenant_id="tenant-a",
    ),
    "manager-a": User(
        id="manager-a",
        roles={"manager"},
        scopes={"invoice:read", "invoice:approve", "invoice:list"},
        tenant_id="tenant-a",
    ),
    "admin-a": User(
        id="admin-a",
        roles={"admin"},
        scopes={"invoice:read", "invoice:list"},
        tenant_id="tenant-a",
    ),
}
