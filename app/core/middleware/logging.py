import time

import structlog
import uuid6
from fastapi import FastAPI, Request
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.utils import get_client_ip

logger = structlog.get_logger()


def register_logging_middleware(app: FastAPI):
    @app.middleware("http")
    async def log_and_trace_request(request: Request, call_next):
        start_time = time.time()
        request_method = request.method
        request_path = request.url.path
        client_ip = get_client_ip(request)
        request_id = request.headers.get("X-Request-ID", str(uuid6.uuid7()))

        clear_contextvars()
        bind_contextvars(
            request_method=request_method,
            request_path=request_path,
            client_ip=client_ip,
            request_id=request_id,
        )

        response = await call_next(request)
        process_time = round((time.time() - start_time) * 1000, 2)

        logger.info(
            "Request completed",
            status_code=response.status_code,
            latency_ms=process_time,
        )
        return response
