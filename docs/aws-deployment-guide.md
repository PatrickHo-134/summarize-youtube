Here is the step-by-step guide to packaging your code, deploying it to AWS Lambda, and exposing it to the internet via API Gateway.

# **1. Create the Deployment Package:**
AWS Lambda requires all external libraries to be bundled with your code..

Open your terminal in the root directory of your project and run these commands to create a `.zip` file containing your script and its dependencies:

Bash
```
# 1. Create a temporary folder for packaging
mkdir package

# 2. Install production dependencies into this folder
pip install -r requirements.txt --target ./package

# 3. Copy your Lambda function into the folder
cp src/lambda_function.py package/

# 4. Zip the contents (ensure you are inside the folder so paths align)
cd package
zip -r ../deployment.zip .

# 5. Go back to the root directory
cd ..

```

You should now have a `deployment.zip` file in your project root.

# **2.Create the Lambda Function:**
Upload your code to the cloud..

1.  Log in to the [AWS Management Console](https://console.aws.amazon.com/) and search for **Lambda**.

2.  Click **Create function**.

3.  Select **Author from scratch**.

4.  **Function name:** `youtube-summarizer`

5.  **Runtime:** Python 3.12 (or 3.11)

6.  **Architecture:** x86_64

7.  Click **Create function**.

8.  On the function page, look for the **Code source** section. Click **Upload from** > **.zip file** and upload your `deployment.zip`.

9.  Under **Runtime settings** (below the code editor), ensure the **Handler** is set to `lambda_function.lambda_handler`.

# **3.Configure Lambda Settings:**
Critical for connecting to OpenAI and preventing timeouts..

1.  Navigate to the **Configuration** tab.

2.  Select **Environment variables** on the left, then click **Edit** and add your keys:

    -   Key: `OPENAI_API_KEY` | Value: *your-secret-key*

    -   Key: `OPENAI_ORG_ID` | Value: *your-org-id*

    -   Key: `OPENAI_PROJECT_ID` | Value: *your-project-id*

3.  Select **General configuration** on the left, then click **Edit**.

4.  Change the **Timeout** from 3 seconds to **30 seconds** (or 1 minute). LLMs take time to generate text, and the default 3 seconds will cause your function to fail prematurely.

# **4.Set Up API Gateway:**
Create a public URL for your UI to call..

1.  Search for **API Gateway** in the AWS console.

2.  Under **HTTP API**, click **Build**.

3.  Click **Add integration**, select **Lambda**, and choose your `youtube-summarizer` function. Name the API (e.g., `youtube-summarizer-api`) and click Next.

4.  **Configure routes:**

    -   Method: `POST`

    -   Resource path: `/summarize`

    -   Integration target: `youtube-summarizer`

5.  Click **Next** until you reach **Create**.

# **5.Configure CORS:**
Browsers block requests without this..

1.  In your new API Gateway, click **CORS** in the left-hand menu.

2.  Click **Configure** and set the following parameters:

    -   **Access-Control-Allow-Origin:** `*` (Or you can restrict this to your specific domain later)

    -   **Access-Control-Allow-Headers:** `content-type`

    -   **Access-Control-Allow-Methods:** `POST, OPTIONS`

3.  Click **Save**.

# **6.Update the UI:**
Connect the frontend to the backend..

1.  In the API Gateway console, find your **Invoke URL** (it will look like `[https://abcdefg.execute-api.region.amazonaws.com](https://abcdefg.execute-api.region.amazonaws.com)`).

2.  Open your `index.html` file.

3.  Replace `YOUR_AWS_API_GATEWAY_URL_HERE` with your Invoke URL, appended with your route:

JavaScript

```
const API_ENDPOINT = 'https://abcdefg.execute-api.us-east-1.amazonaws.com/summarize';

```

4.  Save `index.html` and double-click it to open it in your browser. Paste a YouTube URL and hit Summarize!