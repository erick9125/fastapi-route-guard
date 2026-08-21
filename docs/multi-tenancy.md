# Multi-tenancy

When `tenant=True`, the principal and the resource must share a tenant.

```python
Depends(
    guard.protect_resource(
        "invoice",
        id_param="invoice_id",
        scopes={"invoice:read"},
        tenant=True,
    )
)
```

`TenantEvaluator` allows the request only when both `principal.tenant_id` and
`attributes.tenant_id` are present and equal. A missing value on either side is
a deny.

This is not tenancy as a product feature: there is no tenant registry, no
subdomain routing, and no row-level SQL filter. The library compares two
strings the application mapped onto the principal and the resource.

List endpoints (`GET /invoices`) are not filtered by tenant in `0.1.x`. Protect
the collection with `guard.protect(...)` for roles and scopes, and filter the
query in the application until a later release offers query helpers.
