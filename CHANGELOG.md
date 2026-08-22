# Changelog

## Unreleased

### Fixed

- Resource and attribute resolvers no longer go through a private dependency
  resolver. Their parameters are exposed as real FastAPI dependencies, so
  `yield` dependencies are entered and closed around the request instead of
  arriving as an un-started generator, `app.dependency_overrides` apply to the
  guard as well as to the route, and a dependency shared with the endpoint is
  resolved once per request rather than twice. The claims phase still runs
  before the resolver body, so a denied caller does not trigger the lookup.
- A parameter is treated as the ASGI request only when its annotation *is*
  Starlette's `Request`. A domain class that merely shares the name no longer
  receives the request object.

### Changed

- `add_resource()` must be called before `protect_resource()` for that resource:
  the resolver signature is read when the route is declared. An unregistered
  resource now raises `ResourceNotRegistered` at import time instead of on the
  first request to the endpoint.
- Removed `invoke_callable`, `invoke_resolver`, and `invoke_attributes` from
  `fastapi_route_guard.fastapi.dependencies`.

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
