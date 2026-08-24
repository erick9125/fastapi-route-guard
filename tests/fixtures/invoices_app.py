from dataclasses import dataclass, replace

from fastapi import Depends, FastAPI, Header, HTTPException

from fastapi_route_guard import (
    AuthorizationContext,
    AuthorizationPrincipal,
    ResourceAttributes,
    RouteGuard,
)
from tests.fixtures.invoices import (
    INVOICE_A,
    INVOICE_APPROVED,
    INVOICE_B,
    INVOICE_C,
    Invoice,
)


@dataclass
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


class InvoiceStore:
    def __init__(self) -> None:
        self.find_by_id_calls = 0
        self._items = {
            invoice.id: invoice
            for invoice in (INVOICE_A, INVOICE_B, INVOICE_C, INVOICE_APPROVED)
        }

    def reset(self) -> None:
        self.find_by_id_calls = 0
        self._items = {
            invoice.id: invoice
            for invoice in (INVOICE_A, INVOICE_B, INVOICE_C, INVOICE_APPROVED)
        }

    def find_by_tenant(self, tenant_id: str) -> list[Invoice]:
        return [item for item in self._items.values() if item.tenant_id == tenant_id]

    def find_by_id(self, invoice_id: str) -> Invoice | None:
        self.find_by_id_calls += 1
        return self._items.get(invoice_id)

    def update_amount(self, invoice_id: str, amount: int) -> Invoice | None:
        current = self._items.get(invoice_id)
        if current is None:
            return None
        updated = replace(current, amount=amount)
        self._items[invoice_id] = updated
        return updated

    def approve(self, invoice_id: str) -> Invoice | None:
        current = self._items.get(invoice_id)
        if current is None:
            return None
        updated = replace(current, status="approved")
        self._items[invoice_id] = updated
        return updated

    def remove(self, invoice_id: str) -> Invoice | None:
        return self._items.pop(invoice_id, None)


class InvoiceCanApprove:
    name = "invoice.can_approve"

    async def evaluate(self, context: AuthorizationContext) -> bool:
        invoice = context.resource
        if not isinstance(invoice, Invoice):
            return False
        principal = context.principal
        return (
            invoice.status == "pending"
            and principal is not None
            and "manager" in principal.roles
        )


def create_invoices_app(store: InvoiceStore | None = None) -> FastAPI:
    invoices = store or InvoiceStore()

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

    async def resolve_invoice(invoice_id: str) -> Invoice | None:
        return invoices.find_by_id(invoice_id)

    async def invoice_attributes(invoice: Invoice) -> ResourceAttributes:
        return ResourceAttributes(
            owner_id=invoice.owner_id,
            tenant_id=invoice.tenant_id,
        )

    guard = RouteGuard(principal=current_principal)
    guard.add_resource(
        "invoice",
        resolver=resolve_invoice,
        attributes=invoice_attributes,
    )
    guard.add_policy_handler(InvoiceCanApprove())

    app = FastAPI()
    app.state.store = invoices
    app.state.guard = guard

    @app.get("/invoices")
    async def list_invoices(
        _: None = Depends(
            guard.protect(
                scopes={"invoice:list"},
                roles={"admin", "manager"},
            )
        ),
    ) -> list[Invoice]:
        return invoices.find_by_tenant("tenant-a")

    @app.get("/invoices/{invoice_id}")
    async def get_invoice(
        invoice: Invoice = Depends(
            guard.protect_resource(
                "invoice",
                id_param="invoice_id",
                action="read",
                scopes={"invoice:read"},
                tenant=True,
            )
        ),
    ) -> Invoice:
        return invoice

    @app.patch("/invoices/{invoice_id}")
    async def update_invoice(
        invoice: Invoice = Depends(
            guard.protect_resource(
                "invoice",
                id_param="invoice_id",
                action="update",
                scopes={"invoice:update"},
                tenant=True,
                ownership=True,
            )
        ),
        amount: int = 1,
    ) -> Invoice:
        updated = invoices.update_amount(invoice.id, amount)
        assert updated is not None
        return updated

    @app.post("/invoices/{invoice_id}/approve")
    async def approve_invoice(
        invoice: Invoice = Depends(
            guard.protect_resource(
                "invoice",
                id_param="invoice_id",
                action="approve",
                roles={"manager"},
                scopes={"invoice:approve"},
                tenant=True,
                handler_names=("invoice.can_approve",),
            )
        ),
    ) -> Invoice:
        updated = invoices.approve(invoice.id)
        assert updated is not None
        return updated

    @app.delete("/invoices/{invoice_id}")
    async def delete_invoice(
        invoice: Invoice = Depends(
            guard.protect_resource(
                "invoice",
                id_param="invoice_id",
                action="delete",
                roles={"admin"},
                tenant=True,
            )
        ),
    ) -> Invoice:
        removed = invoices.remove(invoice.id)
        assert removed is not None
        return removed

    guard.validate(app)
    return app
