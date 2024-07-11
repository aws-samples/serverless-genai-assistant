# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
from boto3.dynamodb.conditions import Key
import os


# Get the DynamoDB table name from the environment variable
table_name = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(table_name)


class AccountDataAccess:
    def __init__(self, cognito_access_token):
        # Get the account ID from the Cognito access token
        self.account_id = cognito_access_token.get("custom:account_id")

    def get_account_details(self):
        response = table.query(
            KeyConditionExpression=Key("id").eq(f"account#{self.account_id}") &
                                   Key("item_type").eq("account#details")
        )
        return response.get("Items", [])

    def get_inference_endpoint(self):
        response = table.query(
            KeyConditionExpression=Key("id").eq(f"account#{self.account_id}") &
                                   Key("item_type").eq("account#inference_endpoint")
        )
        return response.get("Items", [])

    def list_workflows(self):
        attributes = ["id", "item_type", "name", "description"]
        expression_attribute_names = {
            f"#{word}": word for word in attributes
        }
        projection_expression = ",".join([f"#{word}" for word in attributes])
        response = table.query(
            KeyConditionExpression=Key("id").eq(f"account#{self.account_id}") &
                                   Key("item_type").begins_with("workflow#details#"),
            ProjectionExpression=projection_expression,
            ExpressionAttributeNames=expression_attribute_names
        )
        return response.get("Items", [])

    def get_workflow_details(self, workflow_id):
        # Split the workflow ID to get the actual ID
        parts = workflow_id.split("#")
        if len(parts) == 3 and parts[0] == "workflow" and parts[1] == "details":
            workflow_id = parts[2]
        else:
            raise ValueError("Invalid item_type string format")
        # get the id from ex: workflow#details#1
        response = table.get_item(
            Key={
                "id": f"account#{self.account_id}",
                "item_type": f"workflow#details#{workflow_id}"
            }
        )

        return response.get("Item", {})

    def list_workflow_prompts(self, workflow_id):
        response = table.query(
            KeyConditionExpression=Key("id").eq(f"account#{self.account_id}") &
                                   Key("item_type").begins_with(f"workflow#prompt#{workflow_id}#")
        )
        return response.get("Items", [])

    def get_workflow_prompt(self, workflow_id, prompt_id):
        response = table.query(
            KeyConditionExpression=Key("id").eq(f"account#{self.account_id}") &
                                   Key("item_type").eq(f"workflow#prompt#{workflow_id}#{prompt_id}")
        )
        return response.get("Items", [])

