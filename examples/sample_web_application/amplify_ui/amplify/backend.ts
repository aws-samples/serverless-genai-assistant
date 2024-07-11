/* Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0 */
import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { preTokenGeneration } from './auth/pre-token-generation/resources';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';


const backend = defineBackend({
  auth,
  preTokenGeneration
});

//https://docs.amplify.aws/react/build-a-backend/auth/modify-resources-with-cdk/#custom-attributes

// extract L1 CfnUserPool resources
const { cfnUserPool } = backend.auth.resources.cfnResources;


// update the schema property to add custom attributes
const user_pool_attributes =  [
      {
    name: 'account_id',
    attributeDataType: 'String',
    mutable: false
  },
  {
    name: 'account_name',
    attributeDataType: 'String',
    mutable: false
  },
  {
    name: 'group_id',
    attributeDataType: 'String',
    mutable: false
  },
  {
    name: 'group_name',
    attributeDataType: 'String',
    mutable: false
  },
  {
    name: 'user_id',
    attributeDataType: 'String',
    mutable: false
  },
  {
    name: 'user_name',
    attributeDataType: 'String',
    mutable: false
  }];


if (Array.isArray(cfnUserPool.schema)) {
  cfnUserPool.schema.push(...user_pool_attributes)
}

//advanced security mode to support customization of access token
cfnUserPool.userPoolAddOns = {
  advancedSecurityMode: 'AUDIT',
};

// Enables request V2_0 to implements access token customization
cfnUserPool.lambdaConfig = {
        preTokenGenerationConfig: {
          lambdaArn:  backend.preTokenGeneration.resources.lambda.functionArn,
          lambdaVersion: 'V2_0',

        }
      }


const invokeFunctionRole = new iam.Role(cfnUserPool, 'CognitoInvokeLambda', {
  assumedBy: new iam.ServicePrincipal('cognito-idp.amazonaws.com')

});

// Loads created preTokenGeneration Lambda on cfnUserPool resource to add Invoke permission
// https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_lambda.FunctionAttributes.html
const createLambdaResourcePolicy = lambda.Function.fromFunctionAttributes(cfnUserPool, 'PreToken Function', {
  functionArn: backend.preTokenGeneration.resources.lambda.functionArn,
  sameEnvironment: true,
  skipPermissions: true
})

createLambdaResourcePolicy.addPermission('invoke-lambda', {
  principal: new iam.ServicePrincipal('cognito-idp.amazonaws.com'),
  action: 'lambda:InvokeFunction',
  sourceArn: cfnUserPool.attrArn,
});





