import pytest

from fastapi_route_guard.testing.principals import test_principal as _test_principal


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    items[:] = [
        item for item in items if getattr(item, "obj", None) is not _test_principal
    ]
