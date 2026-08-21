from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Invoice:
    id: str
    owner_id: str
    tenant_id: str
    status: str
    amount: int


INVOICE_A = Invoice(
    id="invoice-a",
    owner_id="user-a",
    tenant_id="tenant-a",
    status="pending",
    amount=120,
)
INVOICE_B = Invoice(
    id="invoice-b",
    owner_id="user-b",
    tenant_id="tenant-b",
    status="pending",
    amount=90,
)
INVOICE_C = Invoice(
    id="invoice-c",
    owner_id="user-c",
    tenant_id="tenant-a",
    status="pending",
    amount=40,
)
INVOICE_APPROVED = Invoice(
    id="invoice-approved",
    owner_id="user-a",
    tenant_id="tenant-a",
    status="approved",
    amount=15,
)

USER_A = "user-a"
USER_B = "user-b"
USER_C = "user-c"
MANAGER_A = "manager-a"
ADMIN_A = "admin-a"
