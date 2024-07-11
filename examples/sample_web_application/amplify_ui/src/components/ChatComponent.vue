<script setup>
/* Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0 */
import "deep-chat"
import {ref} from "vue";
import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito';

const props = defineProps(['assistantConfig'])
const deepChatInstance = ref(null)


const serverlessAssistantHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': '*',
  'Content-Type': 'application/json',
  'x-amz-content-sha256': '',
  'x-access-token': ''
}

//get Access Token
const getCognitoAccessToken = async () => {
  const accessToken =  cognitoUserPoolsTokenProvider.getTokens().then((tokens) => {
    return tokens.accessToken.toString()
  })
  return accessToken;
}

//Cloudfront requirement to implement the OAC. It will be used to build the SigV4 signature.
const hashPayload = async (payload) => {
        const encoder = new TextEncoder().encode(payload);
        const hash = await crypto.subtle.digest('SHA-256', encoder);
        const hashArray = Array.from(new Uint8Array(hash));
        return hashArray
    .map((bytes) => bytes.toString(16).padStart(2, '0'))
    .join('');

}

const buildServerlessAssistantPayload = async () => {
  const {assistant_url, bedrock_converse_parameters, assistant_parameters } = props.assistantConfig.assistantConfigData();
  //build message pattern for Bedrock Converse API
  bedrock_converse_parameters.messages = BedrockConverseMessages(deepChatInstance.value.getMessages()).messages;
  const payload = JSON.stringify({
      bedrock_converse_parameters: bedrock_converse_parameters,
      assistant_parameters: assistant_parameters
    })

  //Authorization is not used due to the Cloudfront OAC process
  serverlessAssistantHeaders["x-access-token"]= await getCognitoAccessToken();
  serverlessAssistantHeaders["x-amz-content-sha256"] = await hashPayload(payload);

  return {
    url: assistant_url,
    method: 'POST',
    headers: serverlessAssistantHeaders,
    body: payload
  }
}

const BedrockConverseMessages = (deepChatMessages) => {
  /* Convert DeepChat messages format to Amazon Bedrock Converse API
   https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html */
  return {
    messages: deepChatMessages.map((message) => ({
      content: [{text: message.text}],
      role: ((message.role === 'ai') ? 'assistant' : 'user'),
    })),
  };

}

const requestHandler = {
  handler: async (body, signals) => {
    let requestData = await buildServerlessAssistantPayload();
    fetch(requestData.url, requestData).then(response => {
      // Check if the response is readable as a stream
      if (response.ok && response.body && response.body.getReader) {
        signals.onOpen();
        // Create a reader object to read the stream
        const reader = response.body.getReader();
        // Read the stream in chunks using the reader
        const readChunks = {
          value: null,
          done: false,
          read() {
            // Read the next chunk from the stream
            reader.read().then(({done, value}) => {
              if (done) {
                // Stream finished
                this.done = true;
                signals.onClose();
                return;
              }
              processChunk(value);
              this.read();
            });
          }
        };
        // Start reading the stream
        readChunks.read();
      } else {
        signals.onResponse({text: "Error from server. Please try again later."})
        signals.onClose();
      }
    })
        .catch(error => {
          signals.onResponse({error: error})
          signals.onClose()
        });

    function processChunk(chunk) {
      // Process the chunk of data (e.g., append to a string or buffer)
      signals.onResponse({text: new TextDecoder().decode(chunk)})
    }
  }
}

</script>

<template>
  <div class="chat-container">
  <deep-chat
      ref="deepChatInstance"
      :request=requestHandler
      id="deep-chat-instance"
      stream="true"

  >
  </deep-chat>
  </div>
</template>

<style scoped>

#deep-chat-instance {
  border-radius: 10px;
  min-width: 30vw !important;
  width: calc(100vw - 30vw) !important;
  height: calc(100vh - 10vh) !important;
}



</style>