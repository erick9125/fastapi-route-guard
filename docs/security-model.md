# Security model

This package does not authenticate users. Authentication must resolve a trusted
principal before `RouteGuard` evaluates a policy.

Resource-level authorization depends on correct resolver and policy
configuration. The library helps enforce consistent object-level authorization
controls that can mitigate BOLA/IDOR risks when correctly configured. It does
not “prevent BOLA” in every application.

## Object-level access

A caller may have `invoice:read` and still be denied invoice `123` if that row
belongs to another tenant or owner. A route without a policy, a resolver that
ignores the id, or a principal mapper that copies the wrong tenant will still
be unsafe.

## HTTP responses

Denied requests return:

```json
{ "detail": "Forbidden" }
```

Internal reason codes and tenant / owner identifiers must not appear in that
body. Missing resources also return `403` rather than `404` so callers cannot
enumerate ids from the status code.

Authentication failures belong to the application's principal dependency and
should remain `401`.

## Enumeration resistance

Nothing is read from storage until the caller has proved they are authenticated
and hold the route's roles and scopes. A caller who fails any of those gets the
same generic `403` whether the id exists or not, and the resolver is never
called.

## Fail closed

Unknown handlers, unknown resource types, duplicate registrations, and thrown
resolvers do not allow access. A thrown resolver is an error, not a deny
decision, and must not be caught and turned into allow.

A policy that names a resource must also check the object — `tenant`,
`ownership`, or a handler — or `protect_resource` raises `MissingObjectCheck`.
`action` is descriptive metadata and never counts as a check.
`unsafe_skip_object_check=True` is the explicit, auditable opt-out.

## Error naming

- `PolicyEvaluationError` and its subclasses are configuration or
  infrastructure faults. They surface as `500`.
- `AuthorizationDenied` is a decision FastAPI turns into HTTP `403`.

Neither ever carries a reason code or a tenant / owner id into the response
body. `AuthorizationDenied.result` is available in-process for tests; it is not
serialized.

## Logging

Safe to log: resource type, action, decision, violation code.

Do not log: tokens, JWTs, cookies, full resources, request bodies, passwords, or
PII.
