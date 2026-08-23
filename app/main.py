from chainlit.utils import mount_chainlit
from fastapi import FastAPI

from app.api.v1.router import v1_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import (
    register_cors_middleware,
    register_exception_handlers,
    register_logging_middleware,
    register_rate_limiter,
    register_trusted_hosts_middleware,
)
from app.core.schemas import ApiResponse

setup_logging()

app = FastAPI(title=settings.api_name, version=settings.api_version)

app.include_router(v1_router, prefix="/api/v1")
mount_chainlit(
    app=app,
    target="frontend/frontend.py",
    path="/chat",
)

register_cors_middleware(app)
register_trusted_hosts_middleware(app)
register_rate_limiter(app)
register_exception_handlers(app)
register_logging_middleware(app)


@app.get("/")
def index():
    return ApiResponse(
        data={
            "api_info": {
                "name": settings.api_name,
                "version": settings.api_version,
            }
        }
    )
