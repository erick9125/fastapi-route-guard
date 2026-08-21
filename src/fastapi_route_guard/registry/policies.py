from collections.abc import Sequence

from fastapi_route_guard.evaluators.custom import PolicyHandler
from fastapi_route_guard.exceptions import DuplicatePolicyHandler, PolicyHandlerNotFound


class PolicyRegistry:
    def __init__(self, handlers: Sequence[PolicyHandler] | None = None) -> None:
        self._handlers: dict[str, PolicyHandler] = {}
        for handler in handlers or ():
            self.register(handler)

    def register(self, handler: PolicyHandler) -> None:
        if handler.name in self._handlers:
            raise DuplicatePolicyHandler(handler.name)
        self._handlers[handler.name] = handler

    def get(self, name: str) -> PolicyHandler:
        try:
            return self._handlers[name]
        except KeyError as exc:
            raise PolicyHandlerNotFound(name) from exc
