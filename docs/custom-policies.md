# Custom policies

Custom handlers are how the library grows without a policy DSL.

```python
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


guard.policy(InvoiceCanApprove())
```

Every name listed in `handlers` must be registered. Missing handlers raise
`PolicyHandlerNotFound` (a configuration fault, not an allow). Every listed
handler must return `True`. Handlers run after claims, resource existence,
tenant, and ownership, so expensive I/O is skipped when a basic scope is
missing — including under `collect_all=True`, which aggregates the violations of
a phase but never runs the next one to collect more.

Handlers are async because they may consult a database, feature flags, or
another authorization context. They receive `AuthorizationContext`: principal,
resource, resource type, action, attributes, and a small request context
(method, path, path params). They should not need the raw `Request`.
