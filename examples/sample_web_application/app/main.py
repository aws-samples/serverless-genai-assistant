# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
from typing import Dict, Any

import boto3
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from api_models.assistant_model import AssistantParameters
from api_models.bedrock_converse_model import BedrockConverseAPIRequest
from api_models.workflow_model import StepFunctionResponse, PromptChainParameters
from assistant_config_interface.data_manager import AccountDataAccess

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.info("Application started")

app = FastAPI(
    title="Serverless GenAI Assistant API",
    description="""This API expects two objects: bedrock_parameters and assistant_parameters. 
    bedrock_parameters holds the standard parameters of Bedrock invoke_model_with_response_stream,
    while assistant_parameters defines behavior for the integration between the lambda and step function,
    allowing data passing between invocations to accelerate LLM applications development"""
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Boto3 clients
bedrock_boto_client = boto3.client("bedrock-runtime")
sf_boto_client = boto3.client("stepfunctions")


def execute_workflow(state_machine_arn: str, input_data: Dict[str, Any]) -> StepFunctionResponse:
    """Execute sync express workflow."""
    logger.info(f"Executing workflow: {state_machine_arn}")
    response = sf_boto_client.start_sync_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps(input_data)
    )

    if response["status"] != "SUCCEEDED":
        error_msg = (
            f"State machine error. Expected: 'SUCCEEDED', Received: {response['status']}. "
            f"Details: ERROR: {response.get('error', 'N/A')}, CAUSE: {response.get('cause', 'N/A')}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    execution_data = StepFunctionResponse.model_validate_json(response['output'])
    logger.debug(f"Step Functions Response: {execution_data}")
    return execution_data


def sf_build_context(
        messages: list,
        system: str,
        assistant_parameters: AssistantParameters,
        data_manager: AccountDataAccess
) -> Dict[str, Any]:
    """Build context """
    logger.info("Retrieving workload configuration")
    workflow_details = data_manager.get_workflow_details(assistant_parameters.workflow_params['workflow_id'])

    logger.info(f"Executing Step Functions State Machine workflow arn: {workflow_details['arn']}")
    sf_workflow_result = execute_workflow(
        state_machine_arn=workflow_details['arn'],
        input_data={
            "PromptInput": messages,
            "state_machine_custom_params": assistant_parameters.state_machine_custom_params,
        },
    )

    context = {
        'system': build_system_context(system, sf_workflow_result.system_chain_data)
    }

    if sf_workflow_result.additional_messages:
        context['additional_messages'] = sf_workflow_result.additional_messages

    return context


def build_system_context(system: str, system_chain_data: PromptChainParameters) -> str:
    """Build system context based on the operation returned from the workflow"""
    logger.debug(f"Building system context with input: system='{system}', system_chain_data={system_chain_data}")

    operation = system_chain_data.operation
    system_chain_prompt = system_chain_data.system_chain_prompt

    if operation == "APPEND":
        return f"{system}\n\n{system_chain_prompt}"
    elif operation == "REPLACE_TAG":
        replace_tag = system_chain_data.configuration.replace_tag
        opening_tag, closing_tag = f"<{replace_tag}>", f"</{replace_tag}>"
        formatted_prompt = f"{opening_tag}{system_chain_prompt}{closing_tag}"
        return system.replace(f"{opening_tag}{closing_tag}", formatted_prompt)
    elif operation == "REPLACE_ALL":
        return system_chain_prompt
    else:
        return system


async def stream_bedrock_converse_api(bedrock_converse_params: BedrockConverseAPIRequest):
    """Stream response from Bedrock converse API."""
    try:
        stream_response = bedrock_boto_client.converse_stream(
            modelId=bedrock_converse_params.model_id,
            messages=bedrock_converse_params.messages,
            system=bedrock_converse_params.system_prompts,
            inferenceConfig=bedrock_converse_params.inference_config,
            additionalModelRequestFields=bedrock_converse_params.additional_model_fields
        )

        stream = stream_response.get('stream')
        if stream:
            for event in stream:
                if 'contentBlockDelta' in event:
                    yield event['contentBlockDelta']['delta']['text']

                if 'metadata' in event:
                    metadata = event['metadata']
                    if 'usage' in metadata:
                        logger.info(f"Token usage: Input tokens: {metadata['usage']['inputTokens']}, "
                                    f"Output tokens: {metadata['usage']['outputTokens']}, "
                                    f"Total tokens: {metadata['usage']['totalTokens']}")
                    if 'metrics' in metadata:
                        logger.info(f"Latency: {metadata['metrics']['latencyMs']} milliseconds")
    except Exception as e:
        logger.error(f"Error in stream_bedrock_converse_api: {str(e)}")
        yield str(e)


@app.post("/bedrock_converse_api")
async def execute_chain_converse_api(
        request: Request,
        bedrock_converse_parameters: BedrockConverseAPIRequest,
        assistant_parameters: AssistantParameters
):
    """Execute the flow with converse API."""
    try:
        request_access_token = json.loads(request.headers['x-access-token'])
        data_manager = AccountDataAccess(request_access_token)

        # Temporary: Format messages for Claude compatibility
        claude_message_format = [
            {"role": message["role"], "content": message["content"][0]["text"]}
            for message in bedrock_converse_parameters.messages
        ]

        chain_data = sf_build_context(
            claude_message_format,
            bedrock_converse_parameters.system_prompts[0]["text"],
            assistant_parameters,
            data_manager
        )

        bedrock_converse_parameters.system_prompts[0]["text"] = chain_data['system']
        bedrock_converse_parameters.messages.extend(chain_data.get('additional_messages', []))

        return StreamingResponse(
            stream_bedrock_converse_api(bedrock_converse_parameters),
            media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Error in execute_chain_converse_api: {str(e)}")
        return StreamingResponse(
            str(e),
            media_type="text/plain; charset=utf-8"
        )