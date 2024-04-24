import requests
import json
from sys import argv
from re import match, IGNORECASE
from system_prompt_samples import rag_prompt_sample



# This is a simple validation to help the user to pass correct lambda url.
# Comment the code snippet if you want to use another url pattern

if argv[1] != "--lambda-url" or not match(
        "https://[a-z0-9]+\\.lambda-url\\.[a-z]{2}-[a-z]+-[0-9]\\.on\\.aws[/]",
        argv[2],
        IGNORECASE,
):
    error_msg = "Arg parse error:\n\
    Invalid arg or url. Check the parameters and try again\n \
    \n\texpected: streamlit run <script.py> -- --lambda-url https://<url-id>.lambda-url.<region>.on.aws/path\n\n"
    print(error_msg)

lambda_url = argv[2]


def stream_bedrock_response():
    
    print("Testing stream bedrock response")




    headers = {"content-type": "application/json"}

    payload = {
        "bedrock_parameters": {
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.9,
            "top_p": 0.999,
            "top_k": 250,
            "max_tokens": 650,
            "stop_sequences": ["\n\nHuman:"],
            "system": '\nYou are an AI assistant to help explain information contained in a JSON data source provided in the "KnowledgeBaseData" array. \n\nThe JSON contains data retrieved from the Amazon Bedrock knowledge base API. Your goal is to reason about this data and provide answers to queries based solely on the content in the "text" fields of the "KnowledgeBaseData".\n\nYou must follow these rules:\n\n1. If the document contains null "text" field, check if the answer was already provided in conversation history, do not invent any data. \n\n2. In your responses, you should infer information from the document while cite relevant verbatim excerpts from the "text" fields that support your reasoning. Do not attempt to infer any other information beyond quoting and explaining \n\n3. Be concerned with using proper grammar and spelling in your explanations, but reproduce excerpts exactly as they appear.\n\n4. Read the document data carefully and use your reasoning capabilities to provide thorough answers to queries.\n\n5. Do not use any external information sources. Answer only based on what can be derived from the provided document content. Do not attempt to infer any other information.\n\n6. If the document contains the atrribute/value "Error: BedrockAgentRuntime.ResourceNotFoundException": 7. Identify that the document is an error message 8. Quote the full error\nmessage verbatim in "Text" attribute, including any relevant details like service name, status code, request ID, etc. 9. Explain that since this is an error message, \nit does not contain information to answer the query directly. 10. Do not attempt to infer any other information beyond quoting and explaining \nthe error message itself. \n\nFor each query, answer with:\n\n- The answer to the query, verbatim, and the explanations.\n- The URI(s) from the corresponding to the source(s)\n- A "score" indicating your confidence in the answer on a 0-1 scale\n\n<examples>\n<query>Human: What is AWS?</query>\n<ideal_response>Assistant: According to the documents {{explanation}} the excerpt {{excerpt}} {{Explanation}} Sources used to answer: {{Uri}} Score: {{score}}</ideal_response>\n<query>Human: What is Infinidash? </query>\n<ideal_response>Assistant: I could not find information to answer that query in the given document.</ideal_response>\n<query>Human: What is Amazon Timestream?</query>\n<Error>BedrockAgentRuntime.ResourceNotFoundException</Error>\n<ideal_response>Assistant: It looks like that Bedrock returned an error. The error is: {{Text}}</ideal_response>\n</examples>\n',
            "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
        },
        "assistant_parameters": {"messages_to_sample": 5, "content_tag": "document"},
    }
    
    response = requests.post(lambda_url, json=payload, headers=headers, stream=True, timeout=60)
    print(response.__dict__)
    print(response.status_code)
    print("end of reponse")

 
    bot_response = ""
    for chunk in response.iter_content(chunk_size=1):
        if chunk:
            new_content = chunk.decode()
            bot_response += new_content
            yield new_content  # Yield only the new content
    return bot_response  # Return the complete bot response


if __name__ == "__main__":
    data = stream_bedrock_response()
    for chunk in data:
        print(chunk)