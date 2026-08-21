from enum import StrEnum


class ViolationCode(StrEnum):
    UNAUTHENTICATED = "unauthenticated"
    MISSING_ROLE = "missing_role"
    MISSING_SCOPE = "missing_scope"
    TENANT_MISMATCH = "tenant_mismatch"
    OWNERSHIP_MISMATCH = "ownership_mismatch"
    RESOURCE_NOT_FOUND = "resource_not_found"
    CUSTOM_POLICY_DENIED = "custom_policy_denied"
