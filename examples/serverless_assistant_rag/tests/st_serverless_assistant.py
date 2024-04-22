# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import streamlit as st
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
    st.error(error_msg)
    st.error("Got: " + argv[1] + " " + argv[2])
    print(error_msg)
    print("Press CTRL+C to exit")
    st.stop()
# End of url check

# lambda url
lambda_url = argv[2]

# Prompt engineering that will be used to invoke Bedrock in lambda function. Note that this prompt contains the
# instructions to answer to the user. Each Task in step functions will have an individual prompt.
system_prompt = rag_prompt_sample


greetings = """Welcome to sample **Serverless GenAI Assistant**! :wave: The default prompt instructions is intended 
to answer questions based on a Knowledge Base. If you do not have one, check this guide: KB (
https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html) If you want to obtain different 
answers, edit the prompt instruction in the system parameter to obtain different results"""

st.title("Serverless GenAI Assistant")
st.set_page_config.page_title = "Serverless GenAI Assistant"
# Create a container for the welcome message
welcome_container = st.container()

# Add the welcome message to the container
with welcome_container:
    st.info(greetings)


def stream_bedrock_response():
    headers = {"content-type": "application/json"}

    payload = {
        "bedrock_parameters": {
            "messages": st.session_state.messages,
            "temperature": float(temperature),
            "top_p": float(top_p),
            "top_k": int(top_k),
            "max_tokens": int(max_tokens),
            # transform string in list separated by comma #
            "stop_sequences": stop_sequences.split(","),
            "system": str(system),
            "modelId": str(model_id),
        },
        "assistant_parameters": {
            "messages_to_sample": messages_to_sample,
            "content_tag": "document",
            "state_machine_custom_params": {"hello": "state_machine"},
        },
    }

    response = requests.post(lambda_url, json=payload, headers=headers, stream=True, timeout=60)

    if response.status_code == 200:
        bot_response = ""
        for chunk in response.iter_content(chunk_size=256):
            if chunk:
                new_content = chunk.decode()
                bot_response += new_content
                yield new_content  # Yield only the new content
        return bot_response  # Return the complete bot response
    else:
        yield "An error occurred while processing the response"

    #print(st.session_state.messages)


# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Add widgets for configuring parameters
temperature = st.sidebar.slider(
    "Temperature", min_value=0.0, max_value=1.0, value=0.9, step=0.1
)
# top_p = st.sidebar.slider("Top-p", min_value=0.0, max_value=1.0, value=0.999, step=0.001)
top_p = st.sidebar.slider(
    "Top-p", min_value=0.0, max_value=1.0, value=0.999, step=0.001, format="%.3f"
)
top_k = st.sidebar.number_input("Top-k", min_value=1, value=250, step=1)
max_tokens = st.sidebar.number_input(
    "max_tokens", min_value=1, max_value=2000, value=650, step=1
)
stop_sequences = st.sidebar.text_input("Stop Sequences", value="\n\nHuman:")
system = st.sidebar.text_area("System", value=system_prompt)
model_id = st.sidebar.radio(
    "Model ID",
    [
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
    ],
    index=1,
)
messages_to_sample = st.sidebar.number_input(
    "Messages to Sample (last N messages to sent to Step Function)",
    min_value=1,
    max_value=20,
    value=5,
    step=1,
)

# Keep messages on rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Prompt"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message
    with st.chat_message("assistant"):
        assistant_response = st.write_stream(stream_bedrock_response())

    #if the last message there is two messages with the same role, ask the user to wait the response.
    # Add response to chat history
    st.session_state.messages.append(
        {"role": "assistant", "content": assistant_response}
    )
