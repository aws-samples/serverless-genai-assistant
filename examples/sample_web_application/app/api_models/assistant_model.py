from typing import Optional
from pydantic import BaseModel, Field


class AssistantParameters(BaseModel):
    messages_to_sample: int = Field(
        default="5",
        description="Number of last message history that will be sent to the workflow",
    )
    workflow_params:  dict = Field(
        default="workflow#details#1",
        description="Additional params to use as data in workflow"
    )
    state_machine_custom_params: dict = Field(
        default={},
        description="Additional params to handle in the workflow"
    )
