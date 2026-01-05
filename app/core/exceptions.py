class DomainException(Exception):
    pass


class NotFoundException(DomainException):
    pass


class ConflictException(DomainException):
    pass


class ValidationDomainException(DomainException):
    pass


class UnauthorizedException(DomainException):
    pass
