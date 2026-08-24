from fastapi import Depends, FastAPI

from examples.invoices_api.auth import current_principal
from examples.invoices_api.models import Invoice
from examples.invoices_api.policies import InvoiceCanApprove
from examples.invoices_api.store import InvoiceStore
from fastapi_route_guard import ResourceAttributes, RouteGuard

store = InvoiceStore()


async def resolve_invoice(invoice_id: str) -> Invoice | None:
    return await store.find_by_id(invoice_id)


async def invoice_attributes(invoice: Invoice) -> ResourceAttributes:
    return ResourceAttributes(owner_id=invoice.owner_id, tenant_id=invoice.tenant_id)


guard = RouteGuard(principal=current_principal)
guard.add_resource("invoice", resolver=resolve_invoice, attributes=invoice_attributes)
guard.add_policy_handler(InvoiceCanApprove())

app = FastAPI(title="FastAPI Route Guard invoices example")


@app.get("/invoices")
async def list_invoices(
    _: None = Depends(
        guard.protect(scopes={"invoice:list"}, roles={"admin", "manager"})
    ),
) -> dict[str, str]:
    return {"status": "ok"}


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
    updated = store.update_amount(invoice.id, amount)
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
    updated = store.approve(invoice.id)
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
    removed = store.remove(invoice.id)
    assert removed is not None
    return removed


# Wiring is checked once, at import time, instead of on the first request.
guard.validate(app)
