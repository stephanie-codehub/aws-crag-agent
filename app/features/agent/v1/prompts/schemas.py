from pydantic import BaseModel, Field


class PromptMetadataSchema(BaseModel):
    version: str
    name: str
    description: str


class PromptModelSettingsSchema(BaseModel):
    model: str
    model_provider: str
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, gt=0)


class PromptTemplateSchema(BaseModel):
    metadata: PromptMetadataSchema
    model_settings: PromptModelSettingsSchema
    system_prompt: str
    user_prompt: str
