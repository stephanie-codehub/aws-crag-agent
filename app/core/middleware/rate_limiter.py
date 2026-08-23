from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from app.core.utils import get_client_ip

limiter = Limiter(
    key_func=get_client_ip,
    storage_uri="memory://",  # redis://localhost:6379 for local dev
    default_limits=["60/minute"],
)


def register_rate_limiter(app):
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
