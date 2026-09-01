import uuid
from langgraph.config import get_stream_writer

from fastapi import Request
from fastapi.templating import Jinja2Templates
import structlog
from app.core.exceptions import ResourceNotFoundException

logger = structlog.get_logger()

templates = Jinja2Templates(directory="templates/email")
PRODUCT_NAME = "Cuomo"


def render_email_template(template_name: str, template_vars: dict | None = None) -> str:
    """Loads an HTML template and compiles it with dynamic data."""
    merged_vars = {"product_name": PRODUCT_NAME}
    if template_vars:
        merged_vars.update(template_vars)
    html = templates.env.get_template(template_name).render(merged_vars)
    return html


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )

    return client_ip


def validate_resource_ownership(
    current_user_id: uuid.UUID, resource_user_id: uuid.UUID
):
    if current_user_id != resource_user_id:
        raise ResourceNotFoundException()


def log_node_status(message: str):
    """Global helper to emit graph status messages."""
    try:
        writer = get_stream_writer()
        if writer:
            writer(message)
    except Exception:
        logger.exception("Error getting Langgraph stream writer")
