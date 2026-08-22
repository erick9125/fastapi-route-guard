import inspect
from collections.abc import Awaitable, Callable, Collection
from typing import Any, cast, get_type_hints


def callable_from(target: object) -> Callable[..., Any]:
    resolve = getattr(target, "resolve", None)
    if callable(resolve) and not isinstance(target, type):
        return cast(Callable[..., Any], resolve)
    if callable(target):
        return cast(Callable[..., Any], target)
    raise TypeError(f"Cannot use {target!r} as an async callable resolver.")


def id_parameter(call: Callable[..., Any], id_param: str) -> str:
    """Name of the parameter the resource id is bound to.

    A resolver may name it after the path parameter or use the generic
    ``resource_id``.
    """
    names = _parameter_names(call)
    if id_param in names:
        return id_param
    if "resource_id" in names:
        return "resource_id"
    return id_param


def resource_parameter(call: Callable[..., Any]) -> str:
    """Name of the parameter the loaded resource is bound to.

    An attributes resolver may name it ``resource`` or take the resource as its
    first argument.
    """
    names = _parameter_names(call)
    if "resource" in names:
        return "resource"
    if not names:
        raise TypeError(f"{call!r} must accept the loaded resource as an argument.")
    return names[0]


def collector_for(
    call: Callable[..., Any],
    *,
    exclude: Collection[str],
) -> Callable[..., Awaitable[dict[str, Any]]]:
    """Expose the parameters of ``call`` the guard does not bind itself.

    The returned function carries ``call``'s remaining signature, so FastAPI —
    not this library — resolves them: ``Depends`` (including ``yield``
    dependencies and their teardown), ``dependency_overrides``, the per-request
    cache, ``Request``, and path or query parameters. It hands the resolved
    values back as keyword arguments, so the resolver itself stays lazy and
    only runs once the claims phase has passed.
    """
    hints = _resolved_annotations(call)
    parameters = [
        param.replace(
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=hints.get(name, param.annotation),
        )
        for name, param in inspect.signature(call).parameters.items()
        if name not in exclude
        and param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD)
    ]

    async def collect(**kwargs: Any) -> dict[str, Any]:
        return kwargs

    collect.__signature__ = inspect.Signature(parameters)  # type: ignore[attr-defined]
    collect.__name__ = f"collect_{getattr(call, '__name__', 'dependencies')}"
    return collect


async def call_resolver(call: Callable[..., Any], **kwargs: Any) -> Any:
    result = call(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def _parameter_names(call: Callable[..., Any]) -> list[str]:
    return [
        name
        for name, param in inspect.signature(call).parameters.items()
        if param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD)
    ]


def _resolved_annotations(call: Callable[..., Any]) -> dict[str, Any]:
    try:
        return get_type_hints(call, include_extras=True)
    except Exception:
        # An unresolvable forward reference is the caller's problem to report;
        # falling back to the raw annotations keeps wiring from crashing here.
        return {}
