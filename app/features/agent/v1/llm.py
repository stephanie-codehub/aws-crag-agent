from app.features.agent.v1.prompts.schemas import PromptModelSettingsSchema
from langchain.chat_models import init_chat_model


def create_llm_client(prompt_model_settings: PromptModelSettingsSchema):
    model_parameters = prompt_model_settings.model_dump()
    llm = init_chat_model(
        **model_parameters,
        model_kwargs={"extra_body": {"reasoning_format": "hidden"}},
    )
    return llm
