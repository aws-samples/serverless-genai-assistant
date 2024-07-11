import type { PreTokenGenerationTriggerHandler } from "aws-lambda";

//https://aws.amazon.com/blogs/security/how-to-customize-access-tokens-in-amazon-cognito-user-pools/
//https://docs.amplify.aws/vue/build-a-backend/functions/examples/override-token/


//Note that any is used here to allow the usage of access token customization.
export const handler: any = async (event: any) => {
  event.response = {
    claimsAndScopeOverrideDetails: {
    accessTokenGeneration: {
      claimsToAddOrOverride: {
        "custom:account_id": event.request.userAttributes["custom:account_id"]
      },
    }
    }
  };
  return event;
};