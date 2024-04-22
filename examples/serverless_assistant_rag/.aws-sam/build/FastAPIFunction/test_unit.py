import pytest
import sys

sys.path.append('.')
from main import sf_build_chain_content, sf_build_context, execute_workflow

content = {
    "bedrock_details": {"task_details": [{"task_name": "task1",
                                          "task_model_id": "XXXXXX",
                                          "input_token": 1,
                                          "output_token": 2}],
                        "total_input_tokens": 3,
                        "total_output_tokens": 4},
    "context_data": ["NOPE"],
    "prompt_chain_data": {
        "prompt": "hello",
        "operation": "APPEND"
    }
}

output_result = """ {
    "bedrock_details": {
        "task_details": [
            {
                "task_name": "task0",
                "task_model_id": "claude-3-haiku-48k-20240307",
                "output_token": 11,
                "input_token": 78
            },
            {
                "task_name": "task0",
                "task_model_id": "claude-3-haiku-48k-20240307",
                "output_token": 11,
                "input_token": 78
            }
        ],
        "total_output_tokens": 15,
        "total_input_tokens": 192
    },
    "context_data": [
        {
            "Text": "Did you created the Bedrock KB? Check the URL: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html",
            "Cause": "Knowledge Base with id KX56LIE8VG does not exist (Service: BedrockAgentRuntime, Status Code: 404, Request ID: 54bcb7cf-2d64-4f73-bb8d-e7afc9abd9e3)",
            "Error": "BedrockAgentRuntime.ResourceNotFoundException"
        }
    ],
    "prompt_chain_data": {
        "prompt": "hello",
        "operation": "REPLACE_TAG",
        "configuration": {
            "replace_tag": ""
        }
    }
}
"""

def test_execute_workflow(mocker):
    environ = {"STATEMACHINE_STATE_MACHINE_ARN": "AAA"}

    mocker.patch('main.environ', environ)
    mocker_boto = mocker.patch('main.sf_boto_client.start_sync_execution')
    mocker_boto.return_value = {"status": "SUCCEEDED", "output": output_result}
    messages = [{'role': 'user', 'message': 'ola'}]
    state_machine_custom_params = {'hello': 'world'}
    sf_worflow = execute_workflow("AAA", input_data={
        "PromptInput": messages,
        "state_machine_custom_params": state_machine_custom_params
    })
    result = sf_worflow


def test_sf_build_chain_content(mocker):
    environ = {"STATEMACHINE_STATE_MACHINE_ARN": "AAA"}
    mocker.patch('main.environ', environ)
    mocker.patch('main.sf_build_context')
    mock_execute_workflow = mocker.patch('main.execute_workflow')
    mock_execute_workflow.return_value = content
    system = "You are a helpful assistant."
    sf_data = sf_build_context(
        messages=[{'role': 'user', 'message': 'ola'}],
        system='hi',
        content_tag='doc',
        state_machine_custom_params={'hello': 'world'}
    )
    tag = "DOCUMENT"
    result = sf_data
    assert result == "hi\n\n<doc>['NOPE']</doc>"


def test_sf_build_chain_content_boto_mock(mocker):
    environ = {"STATEMACHINE_STATE_MACHINE_ARN": "AAA"}
    mocker.patch('main.environ', environ)
    mocker.patch('main.sf_build_context')
    mocker_boto = mocker.patch('main.sf_boto_client.start_sync_execution')
    mocker_boto.return_value = {"status": "SUCCEEDED", "output": output_result}
    system = "You are a helpful assistant."
    sf_data = sf_build_context(
        messages=[{'role': 'user', 'message': 'ola'}],
        system='hi',
        content_tag='doc',
        state_machine_custom_params={'hello': 'world'}
    )
    tag = "DOCUMENT"
    result = sf_data
    assert result == "hi\n\n<doc>['NOPE']</doc>"
