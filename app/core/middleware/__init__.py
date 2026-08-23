from app.core.middleware.cors import register_cors_middleware
from app.core.middleware.exception_handler import register_exception_handlers
from app.core.middleware.logging import register_logging_middleware
from app.core.middleware.rate_limiter import register_rate_limiter
from app.core.middleware.trusted_hosts import register_trusted_hosts_middleware

__all__ = [
    "register_cors_middleware",
    "register_exception_handlers",
    "register_logging_middleware",
    "register_rate_limiter",
    "register_trusted_hosts_middleware",
]
