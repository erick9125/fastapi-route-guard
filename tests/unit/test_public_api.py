import fastapi_route_guard


def test_no_public_symbol_looks_like_a_test() -> None:
    """pytest collects anything named `test_*` that a test module imports.

    A public helper with that prefix turns into a phantom test in every project
    that imports it, so the export list must not contain one.
    """
    collected = [
        name for name in fastapi_route_guard.__all__ if name.startswith("test")
    ]
    assert collected == []


def test_every_exported_name_is_importable() -> None:
    for name in fastapi_route_guard.__all__:
        assert hasattr(fastapi_route_guard, name), name


def test_export_list_is_sorted_and_unique() -> None:
    names = list(fastapi_route_guard.__all__)
    assert names == sorted(names)
    assert len(names) == len(set(names))
