from assistant_config_interface.data_manager import AccountDataAccess
import json


def lambda_handler(event, context):
    try:
        # Extract token claims and path parameters
        claims = event['requestContext']['authorizer']['jwt']['claims']
        path_parameters = event.get('pathParameters', {})

        # Create CustomerDataAccess instance
        account_data = AccountDataAccess(claims)

        # Determine the API route and call the appropriate method
        route_key = event['routeKey']
        account_id = path_parameters.get('accountID')
        workflow_id = path_parameters.get('WorkflowID')

        # Ensure the account_id from the path matches the one in the token
        if account_id != claims.get('custom:account_id'):
            raise ValueError("Account ID in path does not match the one in the token")

        if route_key == 'GET /accounts/{accountID}/account':
            result = account_data.get_account_details()
        elif route_key == 'GET /accounts/{accountID}/inference-endpoint':
            result = account_data.get_inference_endpoint()
        elif route_key == 'GET /accounts/{accountID}/workflows':
            result = account_data.list_workflows()
        elif route_key == 'GET /accounts/{accountID}/workflows/{WorkflowID}':
            if not workflow_id:
                raise ValueError("WorkflowID is required for this endpoint")
            result = account_data.get_workflow_details(workflow_id)
        elif route_key == 'GET /accounts/{accountID}/workflows/{WorkflowID}/prompts':
            if not workflow_id:
                raise ValueError("WorkflowID is required for this endpoint")
            result = account_data.list_workflow_prompts(workflow_id)
        else:
            raise ValueError(f"Unsupported route: {route_key}")

        return {
            'statusCode': 200,
            'body': json.dumps(result),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    except ValueError as ve:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(ve)}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }