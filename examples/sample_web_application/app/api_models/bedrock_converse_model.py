from typing import List, Optional, Union
from pydantic import BaseModel, Field


class MessageContent(BaseModel):
    text: str


class Message(BaseModel):
    role: str
    content: List


class SystemContentBlock(BaseModel):
    text: str


class InferenceConfiguration(BaseModel):
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    #top_p: float = Field(default=0.999, ge=0.0, le=1.0)
    #top_k: int = Field(default=250, ge=0, le=500)
    #max_tokens: int = Field(default=1028, ge=0, le=200000)



class ToolConfiguration(BaseModel):
    # To implement
    pass


class BedrockConverseAPIRequest(BaseModel):
    model_id: str
    additional_model_fields: Optional[dict] = None
    additional_model_fields_paths: Optional[List[str]] = Field(default=[], min_items=0, max_items=10,
                                                                   pattern=r'^/[^/]+(?:/[^/]+)*$')
    inference_config: Optional[dict] = None
    messages: List
    system_prompts: List[dict]
    #tool_config: Optional[ToolConfiguration] = None
