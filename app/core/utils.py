import uuid

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.core.exceptions import ResourceNotFoundException

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
