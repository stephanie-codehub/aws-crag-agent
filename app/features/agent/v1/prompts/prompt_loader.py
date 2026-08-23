from functools import lru_cache
from typing import Any

import yaml
from jinja2 import Template

from app.core.config import settings
from app.features.agent.v1.schemas.prompt_template import PromptTemplateSchema


@lru_cache(maxsize=32)
def _load_file(prompt_name: str, version: str) -> dict:
    file_path = settings.prompts_dir / f"{prompt_name}.yaml"
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_prompt_content(
    prompt_name: str, variables: dict[str, Any], version: str = "v1_0_0"
) -> PromptTemplateSchema:
    """Loads data, validates schemas, and compiles templates into raw text strings."""
    raw_data = _load_file(prompt_name, version)

    # Validate YAML contents with Pydantic
    validated_config = PromptTemplateSchema(**raw_data)

    # Compile text blocks using Jinja2 text rendering
    system_tmpl = Template(validated_config.system_prompt)
    user_tmpl = Template(validated_config.user_prompt)

    validated_config.system_prompt = system_tmpl.render(**variables)
    validated_config.user_prompt = user_tmpl.render(**variables)

    return validated_config
