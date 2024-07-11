import { CognitoJwtVerifier } from "aws-jwt-verify";

/* This is the basic sample.
    Check how this can be improved in the project page at https://github.com/awslabs/aws-jwt-verify */
const verifier = CognitoJwtVerifier.create({
  userPoolId: "<INSERT_USER_POOL_ID>",
  tokenUse: "access",
  clientId: "<INSERT_CLIENT_ID>",
  scope: ["aws.cognito.signin.user.admin"]

});

export const handler = async (event, context, callback) => {
    const request = event.Records[0].cf.request;
    const headers = request.headers;

    const isPreflightRequest =
        request.method === 'OPTIONS' &&
        headers['origin'] &&
        headers['access-control-request-method'];

    if (isPreflightRequest) {
      callback(null, request);
    }

try {
  const payload = await verifier.verify(headers["x-access-token"][0].value);
  console.log("Token is valid. Payload:", payload);
  //Add decoded access token to header
  request.headers["x-access-token"][0].value = JSON.stringify(payload);
  callback(null, request)
} catch {
  console.log("Token not valid!");
  callback(null, {
    status: 403,
    statusDescription: 'Unauthorized'
  })
}
};
