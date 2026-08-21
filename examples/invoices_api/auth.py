from fastapi import Depends, Header, HTTPException

from examples.invoices_api.models import USERS, User
from fastapi_route_guard import AuthorizationPrincipal


async def current_user(x_user: str | None = Header(default=None)) -> User:
    if x_user is None or x_user not in USERS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return USERS[x_user]


async def current_principal(
    user: User = Depends(current_user),
) -> AuthorizationPrincipal:
    return AuthorizationPrincipal(
        id=user.id,
        roles=set(user.roles),
        scopes=set(user.scopes),
        tenant_id=user.tenant_id,
    )
