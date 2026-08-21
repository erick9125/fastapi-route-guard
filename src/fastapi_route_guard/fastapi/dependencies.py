import inspect
from collections.abc import Callable, Mapping
from typing import Annotated, Any, cast, get_args, get_origin

from fastapi.params import Depends
from starlette.requests import Request

_MISSING = object()


def callable_from(target: object) -> Callable[..., Any]:
    resolve = getattr(target, "resolve", None)
    if callable(resolve) and not isinstance(target, type):
        return cast(Callable[..., Any], resolve)
    if callable(target):
        return cast(Callable[..., Any], target)
    raise TypeError(f"Cannot use {target!r} as an async callable resolver.")


def _is_request_annotation(annotation: object) -> bool:
    if annotation is inspect.Parameter.empty:
        return False
    if annotation is Request:
        return True
    return getattr(annotation, "__name__", "") == "Request"


def _depends_from(param: inspect.Parameter) -> Depends | None:
    if isinstance(param.default, Depends):
        return param.default
    origin = get_origin(param.annotation)
    if origin is Annotated:
        for metadata in get_args(param.annotation)[1:]:
            if isinstance(metadata, Depends):
                return metadata
    return None


async def invoke_callable(
    call: Callable[..., Any],
    *,
    request: Request,
    bound: Mapping[str, object] | None = None,
    positional_fallback: object = _MISSING,
) -> Any:
    bound_values = dict(bound or {})
    kwargs: dict[str, Any] = {}
    used_fallback = False

    for name, param in inspect.signature(call).parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if name in bound_values:
            kwargs[name] = bound_values[name]
            continue
        if name == "request" or _is_request_annotation(param.annotation):
            kwargs[name] = request
            continue
        depends = _depends_from(param)
        if depends is not None:
            dependency = depends.dependency
            if dependency is None:
                raise TypeError(
                    f'Depends() on parameter "{name}" has no dependency callable.'
                )
            kwargs[name] = await invoke_callable(dependency, request=request)
            continue
        if (
            not used_fallback
            and positional_fallback is not _MISSING
            and param.default is inspect.Parameter.empty
        ):
            kwargs[name] = positional_fallback
            used_fallback = True
            continue
        if param.default is not inspect.Parameter.empty:
            continue
        if name in request.path_params:
            kwargs[name] = request.path_params[name]
            continue
        raise TypeError(f'Cannot resolve parameter "{name}" for {call!r}.')

    result = call(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


async def invoke_resolver(
    resolver: object,
    *,
    resource_id: str,
    id_param: str,
    request: Request,
) -> Any:
    return await invoke_callable(
        callable_from(resolver),
        request=request,
        bound={
            "resource_id": resource_id,
            id_param: resource_id,
        },
    )


async def invoke_attributes(
    resolver: object,
    resource: object,
    *,
    request: Request,
) -> Any:
    return await invoke_callable(
        callable_from(resolver),
        request=request,
        bound={"resource": resource},
        positional_fallback=resource,
    )
