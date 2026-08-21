# Changelog

## 0.1.0

First release.

### Added

- A FastAPI-free `PolicyEvaluator` covering roles (ANY), scopes (ALL),
  ownership, tenant matching, and custom async handlers. Evaluation runs in two
  phases: principal, roles, and scopes settle in memory, and the resource
  resolver runs only if they pass.
- `RouteGuard` with `protect` and `protect_resource` dependencies. The resource
  guard extracts the path id, authorizes, and returns the loaded object to the
  endpoint so the row is not queried twice.
- Resource and attribute resolvers as async callables, including FastAPI
  `Depends` for nested collaborators such as repositories.
- `AuthorizationDenied` as a generic HTTP 403. Internal violation codes stay
  off the wire. Missing resources are denied with 403, not 404.
- Fail-closed behavior for unknown handlers, unknown resources, duplicate
  registrations, thrown resolvers or handlers, and resource policies that load
  an object without an object-level check.
- `evaluate_policy()` and `test_principal()` testing helpers.
- An example invoices API, plus BOLA / ID-manipulation tests that swap invoice
  ids across tenants and expect `403`.

### Security

- Authentication remains the host application's job (`401`). The guard decides
  authorization (`403`).
- Requirements combine with AND. Claims are evaluated before any resource is
  loaded.
- A policy naming a `resource` must also check the object — `tenant`,
  `ownership`, or a handler — or `protect_resource` raises `MissingObjectCheck`.
  `unsafe_skip_object_check` opts out explicitly.
- Denials return `{"detail": "Forbidden"}`. Reason codes, tenant ids, and owner
  ids stay out of the response body.
