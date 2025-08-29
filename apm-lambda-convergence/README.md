README.md
---------

This project contains a complete demo application designed for deployment on AWS. It includes a containerized Flask frontend, a Python 3.13 Lambda backend, and a CloudFormation template for infrastructure deployment. The frontend can invoke the Lambda function to demonstrate both success and error handling.

### Project Structure

```
.
├── app
│   ├── static
│   │   └── script.js
│   ├── templates
│   │   └── index.html
│   ├── main.py
│   └── requirements.txt
├── lambda
│   └── app.py
├── locust
│   └── locustfile.py
├── .gitignore
├── README.md
├── deploy.sh
├── docker-compose.yml
└── template.yaml

```

### Local Development

To run the frontend application and Locust load tester locally:

1.  **Prerequisites**: Ensure Docker is installed and running.

2.  **Start Services**: Run the following command in your terminal:

    ```
    docker-compose up --build -d

    ```

3.  **Access**:

    -   **Application URL**: `http://localhost:8000`

    -   **Locust UI**: `http://localhost:8089`

### AWS Deployment

To deploy the stack to your AWS account:

1.  **Prerequisites**:

    -   AWS CLI installed and configured with appropriate permissions.

    -   An S3 bucket to store the deployment artifacts.

2.  **Make Script Executable**:

    ```
    chmod +x deploy.sh

    ```

3.  **Run Deployment**:

    ```
    ./deploy.sh YOUR_S3_BUCKET_NAME YOUR_STACK_NAME

    ```

    -   Replace `YOUR_S3_BUCKET_NAME` with the name of your S3 bucket.

    -   Replace `YOUR_STACK_NAME` with the desired name for your CloudFormation stack.

The script will package the Lambda function, upload it to S3, and deploy the CloudFormation template.README.md
---------

This project contains a complete demo application designed for deployment on AWS. It includes a containerized Flask frontend, a Python 3.13 Lambda backend exposed via an HTTP API Gateway, and a CloudFormation template for infrastructure deployment.

### Project Structure

```
.
├── app
│   ├── static
│   │   └── script.js
│   ├── templates
│   │   └── index.html
│   ├── main.py
│   └── requirements.txt
├── lambda
│   └── app.py
├── locust
│   └── locustfile.py
├── .gitignore
├── README.md
├── deploy.sh
├── docker-compose.yml
└── template.yaml

```

### Local Development

To run the frontend application and Locust load tester locally:

1.  **Prerequisites**: Ensure Docker is installed and running.

2.  **Start Services**: Run the following command in your terminal:

    ```
    docker-compose up --build -d

    ```

3.  **Access**:

    -   **Application URL**: `http://localhost:8000`

    -   **Locust UI**: `http://localhost:8089`

> **Note**: When running locally, the Lambda invocation buttons will not work as they are configured to call a deployed AWS API Gateway endpoint.

### AWS Deployment

To deploy the stack to your AWS account:

1.  **Prerequisites**:

    -   AWS CLI installed and configured with appropriate permissions.

    -   An S3 bucket to store the deployment artifacts.

2.  **Make Script Executable**:

    ```
    chmod +x deploy.sh

    ```

3.  **Run Deployment**:

    ```
    ./deploy.sh YOUR_S3_BUCKET_NAME YOUR_STACK_NAME

    ```

    -   Replace `YOUR_S3_BUCKET_NAME` with the name of your S3 bucket.

    -   Replace `YOUR_STACK_NAME` with the desired name for your CloudFormation stack.

The script will package the Lambda, upload it to S3, and deploy the CloudFormation template. After deployment, you will need to configure the API Gateway URL in your frontend's environment variables.