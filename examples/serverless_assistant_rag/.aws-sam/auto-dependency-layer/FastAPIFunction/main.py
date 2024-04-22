from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from os import environ
import json
import boto3


class RequestData(BaseModel):
    messages: list[dict] = [{'role': 'system', 'content': 'You are a helpful assistant.'}]
    temperature: float = 1.0
    top_p: float = 0.999
    top_k: int = 250
    max_tokens: int = 1028
    stop_sequences: list[str] = ['\n\nHuman:']
    modelId: str = 'anthropic.claude-v2:1'
    system: str = ''

app = FastAPI()

#Execute SF flow validation
def execute_workflow(workflow_name, input_data):
    sf_client = boto3.client('stepfunctions')
    sf_payload = sf_client.start_sync_execution(
        stateMachineArn=workflow_name,
        input=json.dumps(input_data)
    )
    return json.loads(sf_payload['output'])

#Validate or Build KB context based on user prompt + context
def validate_or_build_kb(user_prompt, system, context = ''):
    #TODO - Implement error validation
    try:
        sf_workflow = execute_workflow(environ['STATEMACHINE_STATE_MACHINE_ARN'],
                                    {"promptInput": user_prompt, "context": context})
        
        #If SF workflow returns 1 then assume that new KB data was generated
        if sf_workflow['parallelInput'][1]['Body']['content'][0]['text'] == '1':
            #insert the KB data in system parameters - https://docs.anthropic.com/claude/docs/system-prompts
            system = system + '<documento>' + json.dumps(sf_workflow['retrievedData']['RetrievalResults']) + '</documento>'
        return system
    except Exception as e:
        print(e)
        return system

bedrock = boto3.client('bedrock-runtime')
async def bedrock_stream(messages: list, temperature, top_p: float, top_k: int, max_tokens: int, stop_sequences: list[str], modelId: str, system: str):

    body = json.dumps({
        'anthropic_version': 'bedrock-2023-05-31',
        'system': system,
        'messages': [{'content': msg['content'], 'role': msg['role']} for msg in messages], 
        'max_tokens': max_tokens,
        'temperature': temperature,
        'top_k': top_k,
        'top_p': top_p,
        'stop_sequences': stop_sequences
    })
    
    response = bedrock.invoke_model_with_response_stream(
        body=body, modelId=modelId)

    for event in response.get("body"):
        chunk = json.loads(event["chunk"]["bytes"])

        if chunk['type'] == 'message_delta':
            print(f"\nStop reason: {chunk['delta']['stop_reason']}")
            print(f"Stop sequence: {chunk['delta']['stop_sequence']}")
            print(f"Output tokens: {chunk['usage']['output_tokens']}")

        if chunk['type'] == 'content_block_delta':
            if chunk['delta']['type'] == 'text_delta':
                #print(chunk['delta']['text'], end="")
                yield chunk['delta']['text']
    
    
    
    #response = bedrock.invoke_model_with_response_stream(
    #    modelId=modelId,
    #    body=body,
    #    
    #)

    #stream = response.get('body')
    #if stream:
    #    for event in stream:

            
            #chunk = event.get('chunk')
            #if chunk['type'] == 'content_block_delta':
            #    print("DECODE")
            #    print(chunk.get('bytes').decode())
            #    yield json.loads(chunk.get('bytes').decode())['completion']

@app.post("/")
async def index(request_data: RequestData):
    messages = request_data.messages
    temperature = request_data.temperature
    top_p = request_data.top_p
    top_k = request_data.top_k
    stop_sequences = request_data.stop_sequences
    max_tokens = request_data.max_tokens
    modelId = request_data.modelId
    system = request_data.system

    #Execute sf call and add KB to systems content
    #TODO hack - consider add SF call to frontend
    new_system = validate_or_build_kb(messages[-1]['content'], system)
    system = new_system

    return StreamingResponse(bedrock_stream(messages, temperature, top_p, top_k, max_tokens, stop_sequences , modelId, system), media_type="text/plain; charset=utf-8")

   #return StreamingResponse(bedrock_stream(data), media_type="text/plain; charset=utf-8")
