import { defineFunction } from '@aws-amplify/backend';

//https://aws.amazon.com/blogs/security/how-to-customize-access-tokens-in-amazon-cognito-user-pools/
//https://docs.amplify.aws/vue/build-a-backend/functions/examples/override-token/
export const preTokenGeneration = defineFunction({
  name: 'pre-token-generation'
});

