# How to deploy Lambda function

Here is how to package your Python code, deploy it to AWS, and grant it the necessary permissions.

**1.Create the Deployment Package:**AWS requires external libraries to be bundled with your script.

Open your terminal in your project's root directory. You need to install the dependencies into a local folder and zip them together with your code. *(Note: We do not include `boto3` because AWS already provides it in the Lambda environment).*

Bash

```
# 1. Create a temporary packaging directory
mkdir package

# 2. Install only the required external libraries into the package folder
pip install youtube-transcript-api openai -t ./package

# 3. Copy your script into the package folder
cp src/lambda_function.py package/

# 4. Zip the contents (ensure you are inside the folder so paths align correctly)
cd package
zip -r ../deployment.zip .

# 5. Return to the root directory
cd ..

```

You will now have a `deployment.zip` file ready for upload.

**2.Set Up the Lambda Function:**Create the cloud resource.
1.  In the AWS Management Console, navigate to **Lambda** and click **Create function**.

2.  Select **Author from scratch**.

3.  **Function name:** `youtube-summarizer`

4.  **Runtime:** Select the Python version that matches your local environment (e.g., **Python 3.12** or **Python 3.9**).

5.  Click **Create function**.

**3.Deploy Code and Configure Timeout:**Upload your code and adjust the timeout.
1.  On your new function's page, look for the **Code source** section.

2.  Click **Upload from** > **.zip file** and upload your `deployment.zip`.

3.  Navigate to the **Configuration** tab, then select **General configuration** on the left.

4.  Click **Edit** and change the **Timeout** from the default 3 seconds to **30 seconds**. LLMs take time to stream responses, and 3 seconds will cause your function to fail prematurely. Click **Save**.

**4.Attach IAM Permissions:**Grant access to DynamoDB and SSM Parameter Store.

Your Lambda function needs explicit permission to read your database and fetch your secure API key.

1.  Still under the **Configuration** tab, select **Permissions** on the left menu.

2.  Click the link under **Execution role** (it will look like `youtube-summarizer-role-xyz`). This opens the IAM console in a new tab.

3.  In the IAM console, click **Add permissions** > **Attach policies**.

4.  Search for and check the box next to **`AmazonDynamoDBFullAccess`**.

5.  Search for and check the box next to **`AmazonSSMReadOnlyAccess`**.

6.  Click **Add permissions**.

Once your Lambda function is fully deployed and permissions are attached, you can return to the API Gateway console to finish connecting the two.
