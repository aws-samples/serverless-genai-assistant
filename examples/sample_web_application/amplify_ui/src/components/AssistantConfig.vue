<script setup>
/* Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0 */
import {onMounted, ref, watch} from "vue";
import {get} from 'aws-amplify/api';
import {cognitoUserPoolsTokenProvider} from 'aws-amplify/auth/cognito';

const accountId = ref(null);
const accountDetails = ref(null);
const endpointConfig = ref(null);
const workflows = ref([]);
const workflowDetails = ref(null);
const selectedWorkflowId = ref(null);
const loading = ref(true);
const error = ref(null);

async function getCustomerId() {
  const tokens = await cognitoUserPoolsTokenProvider.getTokens();
  accountId.value = tokens.idToken.payload["custom:account_id"];
}

async function getAccessToken() {
  return cognitoUserPoolsTokenProvider.getTokens().then((tokens) => tokens.accessToken.toString());
}

async function fetchData(path) {
  const authToken = await getAccessToken();
  try {
    const restOperation = get({
      apiName: 'AssistantConfigApi',
      path: path,
      options: {
        headers: {
          Authorization: authToken
        }
      }
    });
    const response = await restOperation.response;
    const reader = response.body.getReader();
    const chunks = [];
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      chunks.push(value);
    }
    const responseData = new Uint8Array(chunks.reduce((acc, chunk) => acc + chunk.length, 0));
    let offset = 0;
    for (const chunk of chunks) {
      responseData.set(chunk, offset);
      offset += chunk.length;
    }
    return JSON.parse(new TextDecoder().decode(responseData));
  } catch (error) {
    console.error('API call failed:', error);
    throw error;
  }
}

async function getAccountDetails() {
  try {
    const data = await fetchData(`accounts/${accountId.value}/account`);
    accountDetails.value = data;
    console.log('Account details:', accountDetails.value);
  } catch (error) {
    console.error('Failed to get account details:', error);
  }
}

async function getEndpointConfig() {
  try {
    const data = await fetchData(`accounts/${accountId.value}/inference-endpoint`);
    endpointConfig.value = data;
    console.log('Endpoint config:', endpointConfig.value);
  } catch (error) {
    console.error('Failed to get endpoint config:', error);
  }
}

async function getWorkflows() {
  try {
    const data = await fetchData(`accounts/${accountId.value}/workflows`);
    workflows.value = data;
    console.log('Workflows:', workflows.value);
  } catch (error) {
    console.error('Failed to get workflows:', error);
  }
}

async function getWorkflowDetails() {
  const encodedItem = encodeURIComponent(selectedWorkflowId.value.item_type)
    try {
    const data = await fetchData(`accounts/${accountId.value}/workflows/${encodedItem}`);
    workflowDetails.value = data;
    console.log('Workflow Details:', workflowDetails.value);
  } catch (error) {
    console.error('Failed to get workflow details:', error);
  }
}

onMounted(async () => {
  try {
    loading.value = true;
    await getCustomerId()
    await Promise.all([
      getAccountDetails(),
      getEndpointConfig(),
      getWorkflows()
    ]);
  } catch (e) {
    error.value = "Failed to load data. Please try again later.";
    console.error(e);
  } finally {
    loading.value = false;
  }
});

//loads workflow 0 as selected workflow
watch(workflows, (loadedWorkflows) => {
  if (loadedWorkflows.length > 0 && selectedWorkflowId.value === null) {
    selectedWorkflowId.value = loadedWorkflows[0]
  }
}, { immediate: true } )

//loads workflow configuration for assistant api
watch(selectedWorkflowId, async (newWorkflowSelected) => {
  if (newWorkflowSelected.item_type) {
      try {
        await getWorkflowDetails();
        const workflowAssistantParams = JSON.parse(workflowDetails.value.assistant_params)
        assistantParameters.value.bedrock_converse_parameters = workflowAssistantParams.bedrock_converse_parameters
        assistantParameters.value.assistant_parameters = workflowAssistantParams.assistant_parameters
      } catch (e) {
        console.log("Failed to populate Bedrock Converse API Parameters from Workflow configuration data")
      }
  }
})

const showPanel = ref(true);

const togglePanel = () => {
  showPanel.value = !showPanel.value;
};

/*Validate Converse API Parameters fields*/
const jsonToString = (jsonInput) => {
  return jsonInput.toString()

}
const validateJson = (jsonInput) => {
  try {
    JSON.parse(jsonInput)
    return true
  } catch (e) {
    return false
  }
}
const assistantParameters = ref({
  bedrock_converse_parameters: {
    model_id: "anthropic.claude-3-sonnet-20240229-v1:0",
    inference_config: '{"temperature":0.7, "topP":0.9, "maxTokens":2000}',
    additional_model_fields: '{"top_k":200}',
    additional_model_response_field_paths: "[/stop_sequences]",
    system_prompts: [{
      "text": "You know a lot about serverless, show them"
    }]
  },
  assistant_parameters: {
    messages_to_sample: 5,
    workflow_params: {workflow_id:""},
    state_machine_custom_params:
        '{"hello": "from lambda"}'

  }
})

const createAssistantConfig = () => {
  try {
    const {bedrock_converse_parameters, assistant_parameters} = JSON.parse(JSON.stringify(assistantParameters.value));
        bedrock_converse_parameters.inference_config = JSON.parse(bedrock_converse_parameters.inference_config)
        bedrock_converse_parameters.additional_model_fields = JSON.parse(bedrock_converse_parameters.additional_model_fields)
        assistant_parameters.state_machine_custom_params = JSON.parse(assistant_parameters.state_machine_custom_params)
        assistant_parameters.workflow_params.workflow_id = selectedWorkflowId.value.item_type

    return {
      assistant_url: endpointConfig.value[0].url,
      bedrock_converse_parameters: bedrock_converse_parameters,
      assistant_parameters: assistant_parameters
    }
  } catch (e) {
    console.log(e)
  }
}

const assistantConfigData = createAssistantConfig


defineExpose({assistantConfigData})
</script>

<template>
  <div class="config-area">
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="panel">
      <div class="account-info">
        <h2>Account Information</h2>
        <div v-if="accountDetails" class="info-item">
          <label>Account Name:</label>
          <span>{{ accountDetails[0].name }}</span>
        </div>
        <div v-if="endpointConfig" class="info-item">
          <label>Endpoint Configuration:</label>
          <span>{{ endpointConfig[0].type }}</span>
        </div>
        <div v-if="workflows.length" class="info-item">
          <label>GenAI Flows:</label>
          <select v-model="selectedWorkflowId" >
            <option v-for="workflow in workflows" :key="workflow.id" :value="workflow">
              {{ workflow.name }}
            </option>
          </select>
        </div>
      </div>

      <div class="configuration">
        <h2>Converse API Parameters</h2>
        <div class="input-group">
          <label for="model-id">Model ID:</label>
          <input id="model-id" v-model="assistantParameters.bedrock_converse_parameters.model_id"
                 placeholder="Enter model ID" type="text">
        </div>
        <div class="input-group">
          <label for="parameters-input">Inference Parameters:</label>
          <textarea id="parameters-input" v-model="assistantParameters.bedrock_converse_parameters.inference_config"
                    placeholder="Enter model inference parameters:"></textarea>
                    <p class="error" v-if=!validateJson(assistantParameters.bedrock_converse_parameters.inference_config)>Invalid JSON.</p>
          <a href="https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html" rel="noopener noreferrer"
             target="_blank">Check model inference parameters</a>
        </div>
        <div class="input-group">
          <label for="parameters-input">Additional Model Fields:</label>
          <textarea id="parameters-input"
                    v-model.trim="assistantParameters.bedrock_converse_parameters.additional_model_fields"
                    placeholder="Enter model additional fields"></textarea>
          <p class="error" v-if=!validateJson(assistantParameters.bedrock_converse_parameters.additional_model_fields)>Invalid JSON.</p>
          <a href="https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseStream.html#bedrock-runtime_ConverseStream-request-additionalModelRequestFields"
             rel="noopener noreferrer" target="_blank">Check model additional fields</a>
        </div>
        <div class="input-group">
          <label for="model-id">Additional Model Response Fields</label>
          <input id="model-id"
                 v-model="assistantParameters.bedrock_converse_parameters.additional_model_response_field_paths"
                 placeholder="Response Field Path - Check API Bedrock documentation" type="text">
        </div>
        <div class="input-group">
          <label for="system-input">System:</label>
          <textarea id="system-input" v-model="assistantParameters.bedrock_converse_parameters.system_prompts[0].text"
                    placeholder="Be a nice assistant"></textarea>
          <a href="https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html"
             rel="noopener noreferrer" target="_blank">Check model support</a>
        </div>
        <hr>
        <h2>Assistant Parameters</h2>

        <div class="input-group">
          <label for="messages-to-sample">Messages to Sample:</label>
          <input id="messages-to-sample" v-model="assistantParameters.assistant_parameters.messages_to_sample"
                 placeholder="The last N messages that will be forwarded to Workflow" type="text">
        </div>
        <div class="input-group">
          <label for="custom-params">Custom Params (Will be sent to Workflow):</label>
          <textarea id="custom-params" v-model="assistantParameters.assistant_parameters.state_machine_custom_params"
                    placeholder="Additional parameters that will be sent to workflow"></textarea>
          <p class="error" v-if=!validateJson(assistantParameters.assistant_parameters.state_machine_custom_params)>Invalid JSON.</p>

        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.config-area {
  font-family: Arial, sans-serif;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  background-color: #f5f5f5;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.loading, .error {
  text-align: center;
  padding: 20px;
  font-weight: bold;
}

.error {
  color: #ff0000;
}

.panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.account-info, .configuration {
  background-color: #ffffff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

h2 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #333;
}

.info-item {
  margin-bottom: 10px;
}

.info-item label {
  font-weight: bold;
  margin-right: 10px;
}

.input-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: #555;
}

input, select, textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

textarea {
  min-height: 100px;
  resize: vertical;
}

input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: #6c63ff;
  box-shadow: 0 0 5px rgba(108, 99, 255, 0.3);
}

a {
  display: inline-block;
  margin-top: 5px;
  color: #6c63ff;
  text-decoration: none;
  font-size: 12px;
}

a:hover {
  text-decoration: underline;
}


@media (max-width: 600px) {
  .config-area {
    padding: 10px;
  }
}
</style>