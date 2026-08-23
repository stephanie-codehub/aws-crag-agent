import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.exceptions import AppBaseException, HTMLException
from app.core.schemas import ApiErrorResponse
from app.core.utils import render_email_template

logger = structlog.get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppBaseException)
    async def app_base_exception_handler(request: Request, exc: AppBaseException):
        if exc.status_code >= 500:
            logger.error(exc.message, status_code=exc.status_code, exc_info=exc)
        else:
            logger.warning(
                exc.message,
                status_code=exc.status_code,
            )

        return JSONResponse(
            status_code=exc.status_code,
            content=ApiErrorResponse(
                success=False, message=exc.message, errors=exc.errors
            ).model_dump(mode="json"),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def pydantic_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = {}
        for error in exc.errors():
            field = str(error["loc"][-1]) if error["loc"] else "body"
            errors.setdefault(field, []).append(error["msg"])

        logger.warning(
            "RequestValidationError",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            errors=errors,
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=ApiErrorResponse(
                success=False, message="Validation Failed ", errors=errors
            ).model_dump(mode="json"),
        )

    @app.exception_handler(HTMLException)
    async def html_exception_handler(request: Request, exc: HTMLException):
        error_html = render_email_template("error.html", {"message": exc.message})
        if exc.status_code >= 500:
            logger.error(exc.message, status_code=exc.status_code, exc_info=exc)
        else:
            logger.warning(
                exc.message,
                status_code=exc.status_code,
            )
        return HTMLResponse(content=error_html, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def global_unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled server exception occurred",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=str(exc),
            exc_info=exc,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiErrorResponse(
                message="An unexpected server error occurred.",
            ).model_dump(mode="json"),
        )
