# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from random import random

import boto3
import botocore.exceptions
import json
import uuid
from botocore.config import Config

# This script is used to set up the initial data
# 1 - Populates the DynamoDB table with the initial data.
# 2 - Create a Cognito user to app auth

# configuration data
# AWS profile name and region
profile_name = "<INSERT_PROFILE_NAME>"
region_name = "<INSERT_REGION>"

# Cognito Parameters
user_pool_id = "<INSERT_USER_POOL_ID>"
email = "test@test.com"  # test@test.com works but you can replace it.

# SAM output parameters
table_name = "<INSERT_DYNAMODB_TABLE>"

cloudfront_domain = "<INSERT_CLOUDFRONT_DOMAIN>"

step_functions_arn = "<INSERT_ARN>"

# END of configuration parameters

# generate random number between 10-99
temporary_password = chr(int(random() * 26 + 65)) + "".join([chr(int(random() * 26 + 97)) for _ in range(8)]) + str(
    int(random() * 90 + 10))
special_char = "!@#$%^&*()_+"
temporary_password += special_char[int(random() * len(special_char))]

# generate a random uuid for account_id
account_id = str(uuid.uuid4())

system_prompt = """You are an expert research assistant. Here is a document you will answer questions about:
<chain-information></chain-information>

First, find the quotes from the document that are most relevant to answering the question, and then print them in numbered order. Quotes should be relatively short.

If there are no relevant quotes, write “No relevant quotes” instead.

Then, answer the question, starting with “Answer:“. Do not include or reference quoted content verbatim in the answer. Don’t say “According to Quote [1]” when answering. Instead make references to quotes relevant to each section of the answer solely by adding their bracketed numbers at the end of relevant sentences.

Thus, the format of your overall response should look like what’s shown between the tags. Make sure to follow the formatting and spacing exactly.
Quotes:
[1] “Company X reported revenue of $12 million in 2021.”
[2] “Almost 90% of revenue came from widget sales, with gadget sales making up the remaining 10%.”

Answer:
Company X earned $12 million. [1] Almost 90% of it was from widget sales. [2]


If the question cannot be answered by the document, say so.
"""

# ConverseAPI Parameters for default workflow
assistant_api_params = {"bedrock_converse_parameters": {
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "inference_config": '{"temperature":0.7, "topP":0.9, "maxTokens":2000}',
    "additional_model_fields": '{"top_k":200}',
    "additional_model_response_field_paths": "[/stop_sequences]",
    "system_prompts": [{
        "text": system_prompt
    }]
},
    "assistant_parameters": {
        "messages_to_sample": 5,
        "workflow_params": {"workflow_id": ""},
        "state_machine_custom_params":
            '{"hello": "from configuration database"}'

    }
}

#Initial data
table_items = [
    {"id": {"S": "account#" + account_id}, "item_type": {"S": "account#details"}, "name": {"S": "Default account"},
     "description": {"S": "Test account"}},
    {"id": {"S": "account#" + account_id}, "item_type": {"S": "account#inference_endpoint"},
     "description": {"S": "Endpoint for inference with stream response"},
     "type": {"S": "cloudfront"}, "url": {"S": cloudfront_domain}},
    {"id": {"S": "account#" + account_id}, "item_type": {"S": "workflow#details#1"}, "name": {"S": "Default Workflow"},
     "description": {"S": "Test Workflow for account 1"},
     "type": {"S": "stepfunctions"}, "arn": {"S": step_functions_arn}, "assistant_params": {"S": json.dumps(assistant_api_params)}},
    {"id": {"S": "account#" + account_id}, "item_type": {"S": "workflow#prompt#1#1"},
     "description": {"S": "TODO: Prompt to be used in the step functions workflow."},
     "type": {"S": "text"}, "role": {"S": "user"}, "content": {"S": "Test Workflow for account: " + account_id}}
]


def populate_table():
    print("Populating table with initial data")
    try:
        dynamodb = boto3.Session(profile_name=profile_name, region_name=region_name).client('dynamodb')
    except botocore.exceptions.ClientError as e:
        raise e

    for item in table_items:
        try:
            response = dynamodb.put_item(TableName=table_name, Item=item)
            print("Item added successfully" + str(item['id']) + "|" + str(item['item_type']))
        except Exception as e:
            raise e


def create_cognito_user():
    try:
        cognito = boto3.Session(profile_name=profile_name, region_name=region_name).client('cognito-idp')
    except botocore.exceptions.ClientError as e:
        raise e

    try:
        response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=[
                {
                    "Name": "email",
                    "Value": email
                },
                {

                    "Name": "email_verified",
                    "Value": "true"
                },

                {
                    "Name": "custom:account_id",
                    "Value": account_id
                }
            ],
            TemporaryPassword=temporary_password,
            MessageAction="SUPPRESS"
        )
        print("User created successfully")
        print("*" * 30)
        print("Email: " + email)
        print("Temporary password: " + temporary_password)
        print("*" * 30)
    except Exception as e:
        raise e


if __name__ == "__main__":
    create_cognito_user()
    populate_table()
