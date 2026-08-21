# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a vulnerability

Please open a private security advisory on GitHub or contact the maintainer
directly. Do not file public issues for sensitive disclosures.

## Notes

This package does not authenticate users and does not store credentials.

Authorization denials must not leak tenant ids, owner ids, or internal reason
codes in HTTP responses. Missing resources are denied with `403`, not `404`.

If you find a path that allows access when a policy is present, or that
serializes `AuthorizationResult` to the client, treat it as a security issue.
