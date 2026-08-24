import inspect
from collections.abc import Awaitable, Callable, Collection
from types import UnionType
from typing import (
    Annotated,
    Any,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)
from uuid import UUID

from starlette.requests import Request


class _InvalidId:
    """Marker for a path value that cannot be the declared kind of id."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "INVALID_ID"


INVALID_ID = _InvalidId()

_ID_CONVERTERS: dict[object, Callable[[str], Any]] = {
    str: str,
    int: int,
    UUID: UUID,
}


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
    ``resource_id``. A parameter that asks for the ASGI request is never the id,
    even when the path parameter happens to share its name.
    """
    candidates = [
        name
        for name in (id_param, "resource_id")
        if name in _parameter_names(call) and not _wants_request(call, name)
    ]
    if candidates:
        return candidates[0]
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


def parameter_annotation(call: Callable[..., Any], name: str) -> Any:
    """The resolved annotation of one parameter, or `None` when it has none."""
    annotation = _resolved_annotations(call).get(name)
    if annotation is not None:
        return annotation
    declared = inspect.signature(call).parameters.get(name)
    if declared is None or declared.annotation is inspect.Parameter.empty:
        return None
    return declared.annotation


def coerce_resource_id(value: str, annotation: Any) -> Any:
    """Convert a raw path value to the kind of id the resolver declares.

    Starlette hands every path parameter over as a string, so a resolver that
    asks for an `int` or a `UUID` used to receive text: strict drivers raise and
    key-based stores silently miss, denying a resource the caller does own.

    Returns `INVALID_ID` when the value cannot be that kind of id at all. Such
    an id cannot name an existing resource, so the caller is denied exactly like
    any other miss rather than seeing an error.
    """
    converter = _ID_CONVERTERS.get(_unwrap_annotation(annotation))
    if converter is None:
        return value
    try:
        return converter(value)
    except ValueError:
        return INVALID_ID


async def call_resolver(call: Callable[..., Any], **kwargs: Any) -> Any:
    result = call(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def _wants_request(call: Callable[..., Any], name: str) -> bool:
    annotation = _unwrap_annotation(parameter_annotation(call, name))
    return isinstance(annotation, type) and issubclass(annotation, Request)


def _unwrap_annotation(annotation: Any) -> Any:
    if get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    if get_origin(annotation) in (Union, UnionType):
        present = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(present) == 1:
            annotation = present[0]
    return annotation


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
