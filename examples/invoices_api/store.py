from dataclasses import replace

from examples.invoices_api.models import Invoice


class InvoiceStore:
    def __init__(self) -> None:
        self._items = {
            "invoice-a": Invoice(
                id="invoice-a",
                owner_id="user-a",
                tenant_id="tenant-a",
                status="pending",
                amount=120,
            ),
            "invoice-b": Invoice(
                id="invoice-b",
                owner_id="user-b",
                tenant_id="tenant-b",
                status="pending",
                amount=90,
            ),
            "invoice-c": Invoice(
                id="invoice-c",
                owner_id="user-c",
                tenant_id="tenant-a",
                status="pending",
                amount=40,
            ),
        }

    async def find_by_id(self, invoice_id: str) -> Invoice | None:
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
