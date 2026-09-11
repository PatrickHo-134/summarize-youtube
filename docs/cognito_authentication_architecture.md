YouTube Summarizer - Authentication Mechanism Documentation
===========================================================

This document outlines the architecture, requirements, and implementation steps required to integrate user authentication into the serverless YouTube Summarizer application.

Proposed Authentication Architecture
------------------------------------

The system utilizes **Amazon Cognito User Pools** for identity management, providing secure JWT-based authentication natively integrated with your existing AWS infrastructure.

-   **Frontend Identity:** The React 18 / Vite application will implement the AWS Amplify UI library (`@aws-amplify/ui-react`) to handle login and sign-up flows directly over the existing landing page via a modal overlay.

-   **Edge Protection:** An Amazon API Gateway Cognito User Pool Authorizer will be attached to the `POST /summarize` endpoint (`etx5b18bqf`). This ensures all requests without a valid JWT are blocked at the edge before reaching your backend.

-   **Backend Validation:** The Python 3.13 Lambda function will extract the authenticated user's unique identifier (`sub` claim) passed securely from API Gateway to enforce data ownership and caching logic.

Prerequisites
-------------

Before beginning the implementation, ensure the following tools and access levels are configured:

-   AWS Management Console access or properly configured AWS CLI credentials (IAM permissions for Cognito, API Gateway, DynamoDB, and Lambda).

-   Local development environment running Node.js (v18+) and npm.

-   Existing deployed AWS infrastructure, specifically the API Gateway (`etx5b18bqf`) and the `youtube-summaries` DynamoDB table.

-   Python 3.13 installed locally for updating and packaging the Lambda function.

Detailed Requirements
---------------------

**1\. Progressive Engagement (Lazy Registration)**

-   The unauthenticated landing page design and functionality remain unchanged.

-   When an unauthenticated user clicks the "Submit" button to process a URL, the action is intercepted. A login/sign-up modal is displayed.

-   Upon successful authentication, the modal closes, and the initial URL submission automatically resumes without requiring the user to click "Submit" again.

**2\. API Request Restriction**

-   Only authorized users with valid JWTs issued by Cognito can successfully trigger the `POST /summarize` API Gateway route and invoke the summarizer pipeline.

**3\. Content Visibility and Cost Optimization**

-   Users must only see content related to the URLs they specifically submitted.

-   To prevent duplicate OpenAI and residential proxy costs, the global `youtube-summaries` table (Partition Key: `video_id`) will continue to store the LLM outputs.

-   A new DynamoDB table, `user-submissions`, will act as a mapping layer (Partition Key: `user_id`, Sort Key: `video_id`) to enforce content ownership.

**4\. Future-Proofing (History Views)**

-   The `user-submissions` mapping table intrinsically enables future feature expansion. The application will be able to query all `video_id`s associated with a specific `user_id` to generate a history view for the user.

Backend Implementation Roadmap
------------------------------

The backend infrastructure must be provisioned and configured before any frontend changes can be made or tested.

### Step 1: Provision Amazon Cognito

-   Create an Amazon Cognito User Pool configured for email-based sign-in.

-   Generate an App Client (without a client secret, as this is a browser-based frontend).

-   Note down the generated `userPoolId` and `userPoolClientId`.

### Step 2: Database Expansion

-   Create a new DynamoDB table named `user-submissions`.

-   Set the Partition Key to `user_id` (String) and the Sort Key to `video_id` (String).

### Step 3: Secure API Gateway (`etx5b18bqf`)

-   Navigate to API Gateway and create a new **Cognito User Pool Authorizer** linked to your newly created User Pool.

-   Attach this Authorizer to the `POST /summarize` method under the `Method Request` settings.

-   Ensure the `OPTIONS` method remains unsecured to allow CORS preflight requests to succeed.

-   Redeploy the API Gateway stage (`prod`).

### Step 4: Update Lambda Logic (Python 3.13)

-   Modify your `lambda_function.py` to extract the unique user ID (`sub` claim) from the incoming API Gateway event dictionary: `user_id = event['requestContext']['authorizer']['claims']['sub']`.

-   Implement logic to query the `user-submissions` table first. If a record exists, return the cached summary from `youtube-summaries`.

-   If no record exists, proceed with the OpenAI generation via the residential proxy, cache the new summary in `youtube-summaries` (if it isn't there already), and insert a new mapping record into `user-submissions`.

-   Package the function using your existing cross-platform `build.sh` script (targeting `manylinux2014_x86_64`) and deploy.

Frontend Implementation Roadmap
-------------------------------

Once the backend identifiers are available, update the Vite/React application to implement the authentication flow.

### Step 1: Install Dependencies

Install the required AWS packages via your terminal inside the `/frontend` directory:

Bash

```
npm install aws-amplify @aws-amplify/ui-react

```

### Step 2: Initialize Configuration

In your `main.tsx` or `App.tsx`, initialize the Amplify SDK using the identifiers generated in the backend roadmap:

TypeScript

```
import { Amplify } from 'aws-amplify';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: 'YOUR_USER_POOL_ID',
      userPoolClientId: 'YOUR_USER_POOL_CLIENT_ID',
    }
  }
});

```

### Step 3: Create the Authentication Modal (`AuthModal.tsx`)

-   Create a new component utilizing the `<Authenticator>` component from `@aws-amplify/ui-react`.

-   Use Tailwind CSS v4 to style the component as a fixed overlay with a backdrop blur (e.g., `fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm`).

-   Pass an `onSuccess` callback prop that triggers once the user successfully authenticates.

### Step 4: Intercept Form Submission (`UrlForm.tsx` & `useSummarize.ts`)

-   Modify `UrlForm.tsx` to check the user's authentication state upon clicking the submit button.

-   If unauthenticated, prevent the default form submission (`e.preventDefault()`), store the inputted URL in a temporary state (`pendingUrl`), and set an `isModalOpen` boolean to `true`.

-   Within the `AuthModal`'s `onSuccess` callback, set `isModalOpen` to `false`, retrieve `pendingUrl`, and programmatically invoke your custom `useSummarize` hook.

-   Update `useSummarize.ts` to fetch the Cognito JWT session and append it as a `Bearer` token in the `Authorization` header of the `fetch` request sent to `[https://etx5b18bqf.execute-api.ap-southeast-2.amazonaws.com/prod/summarize](https://etx5b18bqf.execute-api.ap-southeast-2.amazonaws.com/prod/summarize)`.