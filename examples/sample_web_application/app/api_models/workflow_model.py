from typing import List, Literal, Optional
from pydantic import BaseModel, model_validator, Field
from bedrock_converse_model import BedrockConverseAPIRequest


class WorkflowBedrockTaskDetails(BaseModel):
    task_name: str
    task_model_id: str
    input_token: int
    output_token: int


class WorkflowBedrockDetails(BaseModel):
    task_details: List[WorkflowBedrockTaskDetails]
    total_input_tokens: int
    total_output_tokens: int


class PromptChainParametersConfiguration(BaseModel):
    replace_tag: str


class PromptChainParameters(BaseModel):
    system_chain_prompt: str
    operation: Literal["APPEND", "REPLACE_TAG", "REPLACE_ALL"]
    configuration: Optional[PromptChainParametersConfiguration] = None

    # Check REPLACE_TAG configuration
    @model_validator(mode="after")
    def config_validation(cls, step_functions_response, handler):
        if step_functions_response.operation == "REPLACE_TAG" and not step_functions_response.configuration.replace_tag:
            raise ValueError("'REPLACE_TAG' option must be used with configuration.replace_tag str attribute")
        return step_functions_response


class StepFunctionResponse(BaseModel):
    bedrock_details: WorkflowBedrockDetails = Field(
        description="data about bedrock in the workflow"
    )

    context_data: Optional[List] = Field(
        default=[],
        description="Content Returned from State Machine"
    )

    system_chain_data: Optional[PromptChainParameters] = Field(
        default=None,
        description="Prompt Chain Operations"
    )

    additional_messages: Optional[List] = None
