from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse[T](BaseModel):
    """
    Wrapper schema for every success response across the API
    """

    success: bool = True
    message: str = "Request processed successfully"
    data: T | None = None


class ApiErrorResponse(BaseModel):
    """
    Wrapper schema for every error response across the API
    """

    success: bool = False
    message: str
    errors: dict | None = None
