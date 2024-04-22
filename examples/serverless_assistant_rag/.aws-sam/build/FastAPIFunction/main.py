# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from fastapi.responses import StreamingResponse
from typing import List, Optional, Literal
from typing_extensions import Annotated
from pydantic_core import to_json
from pydantic import BaseModel, field_validator, model_validator
from pydantic import Field
from fastapi import FastAPI
from os import environ
import json
import boto3

# Create the FastAPI app
app = FastAPI(
    title="""Sample of a serverless GenAI assistant. it expects two objects. bedrock_parameters and 
    assistant_parameters. while bedrock parameters holds the standard parameters of Bedrock 
    invoke_model_with_response_stream the assistant parameters object define behaviour about the integration between 
    the lambda and step function that allows the user to pass data between the invocations to enhance the llm 
    response quality"""
)

# Boto3 clients for bedrock and step functions
bedrock_boto_client = boto3.client("bedrock-runtime")
sf_boto_client = boto3.client("stepfunctions")


class AssistantParameters(BaseModel):
    # The content_tag will be used to wrap the Step Functions output the defined tag in system prompt by the Step
    # Functions content output.
    content_tag: str = Field(
        default="DOCUMENT",
        description="the name of tag name that will wrap the retrieved content from step functions",
    )
    messages_to_sample: int = Field(
        default="5",
        description="Number of last message history that will be sent to the workflow",
    )
    state_machine_custom_params: dict = Field(
        default={},
        description="Additional params to use as data in workflow"
    )


class BedrockClaudeMessagesAPIRequest(BaseModel):
    """
    This object defines the request body for the Amazon Bedrock using Claude messages API.
    Claude models that supports messaging API - https://docs.anthropic.com/claude/reference/messages,
    Bedrock doc: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModelWithResponseStream.html

    """

    anthropic_version: str = "bedrock-2023-05-31"
    messages: List[dict] = [{"role": "user", "content": "Who are you?"}]
    temperature: float = 1.0
    top_p: float = 0.999
    top_k: int = 250
    max_tokens: int = 1028
    stop_sequences: List[str] = ["\n\nHuman:"]
    modelId: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    system: str = ""


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
    prompt: str
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
        description="usage information about bedrock in the workflow"
    )

    context_data: List = Field(
        default=[],
        description="Content Returned from State Machine"
    )

    prompt_chain_data: Optional[PromptChainParameters] = Field(
        default=None,
        description="Prompt Chain Operations"
    )


# Execute SF sync execution
def execute_workflow(state_machine_arn, input_data):
    response = sf_boto_client.start_sync_execution(
        stateMachineArn=state_machine_arn, input=json.dumps(input_data)
    )
    # raise errors from workflow step executions
    if response["status"] != "SUCCEEDED":
        error_msg = (f"State machine error. Expected: 'SUCCEEDED', Received:"
                     f"{response['status']}. Details:\nERROR: {response['error']},"
                     f"CAUSE: {response['cause']}")
        raise ValueError(error_msg)

    output_data = StepFunctionResponse.model_validate_json(response['output'])
    print(output_data)
    return output_data


# Validate or Build KB context based on user prompt + context
def sf_build_context(messages, system, content_tag, state_machine_custom_params):
    sf_workflow_result = execute_workflow(
        state_machine_arn=environ["STATEMACHINE_STATE_MACHINE_ARN"],
        input_data={
            "PromptInput": messages,
            "state_machine_custom_params": state_machine_custom_params,
        },
    )

    context = sf_build_chain_content(
        system,
        sf_workflow_result,
        content_tag
    )

    return context


def sf_build_chain_content(system: str, sf_data: StepFunctionResponse, content_tag: str) -> str:
    default_content = f"<{content_tag}>{sf_data.context_data}</{content_tag}>"
    if sf_data.prompt_chain_data:
        prompt, operation = sf_data.prompt_chain_data.prompt, sf_data.prompt_chain_data.operation
        if operation == "APPEND":
            return f"{system}\n\n{default_content}\n\n{prompt}"

        elif operation == "REPLACE_TAG":
            replace_tag = sf_data.prompt_chain_data.configuration.replace_tag

            opening_tag = f"<{replace_tag}>"
            closing_tag = f"</{replace_tag}>"

            formatted_prompt = opening_tag + prompt + closing_tag

            return f"{system.replace(opening_tag + closing_tag, formatted_prompt)}\n\n{default_content}"

        elif operation == "REPLACE_ALL":
            return f"{prompt}\n\n{default_content}"

    else:
        return f"{system}\n\n{default_content}"


async def bedrock_stream(bedrock_params):
    try:
        response = bedrock_boto_client.invoke_model_with_response_stream(
            body=to_json(bedrock_params, exclude=["modelId"]),
            modelId=bedrock_params.modelId,
        )
    except Exception as e:
        yield str(e)
    else:
        for event in response.get("body"):
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk["type"] == "content_block_delta":
                if chunk["delta"]["type"] == "text_delta":
                    yield chunk["delta"]["text"]


@app.post("/bedrock_claude_messages_api")
async def execute_chain(
        bedrock_parameters: BedrockClaudeMessagesAPIRequest,
        assistant_parameters: AssistantParameters,
):
    try:
        # Filter the number of message history to be sent to the workflow
        messages = (
            bedrock_parameters.messages[-assistant_parameters.messages_to_sample:]
            if assistant_parameters.messages_to_sample <= len(bedrock_parameters.messages)
            else bedrock_parameters.messages
        )

        system = bedrock_parameters.system
        content_tag = assistant_parameters.content_tag
        custom_params = assistant_parameters.state_machine_custom_params

        # Generate chain instructions and context prompt
        chain_data = sf_build_context(
            messages,
            system,
            content_tag,
            custom_params
        )

        # Update chain instructions and context
        bedrock_parameters.system = chain_data
        print(bedrock_parameters.system)
        return StreamingResponse(
            bedrock_stream(bedrock_parameters),
            media_type="text/plain; charset=utf-8"
        )

    except Exception as e:
        error_message = str(e) + "\n\nRequest content:"
        error_message += f"bedrock_parameters: {bedrock_parameters}"
        error_message += f"\nassistant_parameters: {assistant_parameters}"
        return StreamingResponse(
            error_message,
            media_type="text/plain; charset=utf-8"
        )
