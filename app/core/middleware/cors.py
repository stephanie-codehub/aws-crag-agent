from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def register_cors_middleware(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
