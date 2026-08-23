import importlib

import structlog

from app.core.config import settings

logging = importlib.import_module("logging")


log_level = getattr(logging, settings.api_log_level.upper(), logging.INFO)


def setup_logging():

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )
