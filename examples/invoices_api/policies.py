from examples.invoices_api.models import Invoice
from fastapi_route_guard import AuthorizationContext


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
