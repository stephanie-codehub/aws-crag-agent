from fastapi import status


class AppBaseException(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    message: str = "An error occurred"

    def __init__(
        self,
        message: str | None = None,
        errors: dict | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message or self.message
        self.errors = errors
        self.headers = headers or {}
        super().__init__(self.message)


class DatabaseConnectionError(AppBaseException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "Database connection failed."


class ResourceNotFoundException(AppBaseException):
    status_code = status.HTTP_404_NOT_FOUND
    message = "The requested resource could not be found."


class HTMLException(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    message: str = "Invalid request"


class InvalidAuthTokenException(AppBaseException):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Invalid or expired token"

    def __init__(
        self,
    ):
        headers = {"WWW-Authenticate": "Bearer"}
        super().__init__(message=self.message, headers=headers)


class InvalidRequestException(AppBaseException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Invalid request"
