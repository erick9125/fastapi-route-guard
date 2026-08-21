# Ownership

Ownership is an object-level check: the authenticated principal must be the
owner of the loaded resource.

```python
Depends(
    guard.protect_resource(
        "invoice",
        id_param="invoice_id",
        scopes={"invoice:update"},
        tenant=True,
        ownership=True,
    )
)
```

`OwnershipEvaluator` allows the request only when
`attributes.owner_id is not None` and `attributes.owner_id == principal.id`.

A missing owner id is a deny. Same tenant, wrong owner is also a deny. Tenant
matching and ownership are independent controls; enabling one does not imply
the other.

The application's resource model is not imposed. Map owner identity in the
attributes resolver:

```python
async def invoice_attributes(invoice: Invoice) -> ResourceAttributes:
    return ResourceAttributes(
        owner_id=invoice.user_id,
        tenant_id=invoice.organization_id,
    )
```
