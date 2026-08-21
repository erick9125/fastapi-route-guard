# Limitations

`0.1.x` is an authorization engine for FastAPI HTTP routes. It is not a complete
access-control platform.

Out of scope:

- login, JWT issuance, OAuth, password hashing, user management
- database ACLs, Casbin, OPA, Zanzibar
- Redis, decision caches, OpenTelemetry
- GraphQL, WebSockets, background jobs
- API keys, sessions, rate limiting
- permission dashboards and policy languages
- ORM-specific resolvers
- list/query filtering (`GET /invoices` still needs application filters)

A route without `Depends(guard.protect...)` is not protected by this library.
A resolver that ignores the path id, or a principal mapper that copies a
tenant from the request body, will still be unsafe.

`ContextVar` is intentionally unused: FastAPI dependencies already carry
request context.

Observers and richer composition are deferred to `0.2.x`.
