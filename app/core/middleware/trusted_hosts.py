from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings


def register_trusted_hosts_middleware(app):
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
