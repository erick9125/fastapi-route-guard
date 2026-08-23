class PolicyEvaluationError(Exception):
    pass


class PolicyHandlerNotFound(PolicyEvaluationError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f'No policy handler is registered for "{name}".')


class DuplicatePolicyHandler(PolicyEvaluationError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f'Policy handler "{name}" is already registered.')


class ResourceNotRegistered(PolicyEvaluationError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f'No resource is registered for "{name}".')


class DuplicateResource(PolicyEvaluationError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f'Resource "{name}" is already registered.')


class MissingObjectCheck(PolicyEvaluationError):
    def __init__(self, resource: str) -> None:
        self.resource = resource
        super().__init__(
            f'Resource policy for "{resource}" must declare tenant, ownership, '
            "or a custom handler. Loading a resource without an object-level "
            "check is the BOLA/IDOR class of bug this library exists to prevent."
        )


class InvalidPrincipal(PolicyEvaluationError):
    def __init__(self, dependency: str, received: str) -> None:
        self.dependency = dependency
        self.received = received
        super().__init__(
            f'The principal dependency "{dependency}" returned {received}, not '
            "an AuthorizationPrincipal. Map the application user onto "
            "AuthorizationPrincipal before authorization is evaluated."
        )


class MissingResourceId(PolicyEvaluationError):
    def __init__(self, id_param: str) -> None:
        self.id_param = id_param
        super().__init__(f'Path parameter "{id_param}" is missing from the request.')
