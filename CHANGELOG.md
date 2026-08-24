# Changelog

## 0.1.0

First release.

### Added

- A FastAPI-free `PolicyEvaluator` covering roles (ANY), scopes (ALL),
  ownership, tenant matching, and custom async handlers. Evaluation runs in two
  phases: principal, roles, and scopes settle in memory, and the resource
  resolver runs only if they pass. `collect_all` aggregates the violations of a
  phase without ever running the next one, so a denied caller never triggers the
  I/O of a custom handler.
- `RouteGuard` with `protect` and `protect_resource` dependencies. The resource
  guard extracts the path id, authorizes, and returns the loaded object to the
  endpoint so the row is not queried twice.
- Resource and attribute resolvers as async callables, including FastAPI
  `Depends` for nested collaborators such as repositories. The guard binds the
  resource id and the loaded object; FastAPI resolves everything else, so
  `yield` dependencies are entered and closed around the request,
  `app.dependency_overrides` apply, and a dependency shared with the endpoint is
  resolved once per request.
- The resource id is converted to the kind of id the resolver declares (`int`,
  `UUID`, `str`), since Starlette hands path values over as strings. A value
  that cannot be that kind of id is denied like any other miss, without calling
  the resolver.
- `AuthorizationDenied` as a generic HTTP 403, with optional `detail` and
  `headers`. Internal violation codes stay off the wire. Missing resources are
  denied with 403, not 404.
- Fail-closed behavior for unknown handlers, unknown resources, duplicate
  registrations, thrown resolvers or handlers, and resource policies that load
  an object without an object-level check.
- Configuration faults surface as early as they can be detected. An
  unregistered resource and an unknown handler name fail when the route is
  declared; `RouteGuard.validate(app)` covers what needs the route path and
  raises `IdParameterNotInPath` for an `id_param` the route does not declare; a
  principal dependency that does not return an `AuthorizationPrincipal` raises
  `InvalidPrincipal`, naming the dependency and the type it returned.
- `evaluate_policy()` and `make_principal()` testing helpers.
- An example invoices API, plus BOLA / ID-manipulation tests that swap invoice
  ids across tenants and expect `403`.
- `fastapi_route_guard.__version__`.

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
