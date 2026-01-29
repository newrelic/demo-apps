MSSQL Application on Azure Functions and Azure SQL
====================================================

This project deploys a complete, observable web application and database environment into Microsoft Azure. The purpose is to create a realistic, cost-effective environment for demonstrating full-stack observability with New Relic.

This example runs on Azure Functions and Azure SQL. 

TODO: Add a static web site to serve the content rather than the Azure Function.


## Requirements:

* terraform
* Azure cli "az"
* Azure tools "func"

----------
## Login to Azure CLI

From project root: 
```
az login
```
You should see something like this: 
```
A web browser has been opened at https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize. Please continue the login in the web browser. If no web browser is available or if the web browser fails to open, use device code flow with `az login --use-device-code`.
```

## Get Azure Subscription ID for Terraform: 
```
export ARM_SUBSCRIPTION_ID=$(az account show --query "id" --output tsv) 
```

Verify this worked as expected by viewing your subscription id:

```
echo $ARM_SUBSCRIPTION_ID
```
If you do not see your Azure subscription ID, ensure you are logged in.

----------
## Create Azure Resource Group and Function App with Terraform

This terraform code borrows from the Azure Functions Quickstart examples: [Getting started with Azure Functions](https://learn.microsoft.com/en-us/azure/azure-functions/functions-get-started?pivots=programming-language-python)

In the `terraform` folder:
- Copy `terraform.tvars.example` to `terraform.tvars` 
- Edit to reflect your env:
```
# The admin password for the VM (SSH) and SQL Managed Instance.
# MUST be complex (e.g., "P@ssw0rd12345#")
admin_password   = "YourComplexSQLPassword123#"

# Your local public IP address. Find it by searching "what is my ip" in Google.
# This is required to secure access to the VM.
my_ip_address_start = ""
my_ip_address_end   = ""

# Details for New Relic instrumentation
new_relic_license_key        = "YOUR_INGEST_LICENSE_KEY"
new_relic_app_name           = "YOUR_APP_NAME"
```

Use terraform to create Azure Resource Group, Function App, and Azure SQL DB:
```
terraform init --upgrade 
terraform plan -out main.tfplan -var="runtime_name=python" -var="runtime_version=3.12"
```

Verify the output and when ready apply the changes: 
```
terraform apply main.tfplan
```

This will run for a few minutes and display progress. When finsished, you should see an output similar to this:
```
admin_password = "complex_password_here_123 "
asp_name = "vvwzuybj"
fa_name = "vvwzuybj"
fa_url = "https://vvwzuybj.azurewebsites.net"
resource_group_name = "rg-crisp-ostrich"
sa_name = "vvwzuybj"
sql_server_name = "sql-helped-rhino"
```
----

## Add the stored procedres for the demo
This will download `sqlcmd` for your platform and run the  `stored_procedures.ql` file aginst the DB
```
../scripts/configuresql.sh
```
----
## Test locally



**To send to New Relic you will need to export the following envvars:**
```
NEW_RELIC_LICENSE_KEY=<Your New Relic Key>
NEW_RELIC_APP_NAME=<Your New Relic app name>
```


From the terraform directory: 
```
export DB_SERVER=$(terraform output -raw sql_server_name)
export MSSQL_SA_PASSWORD=$(terraform output -raw admin_password)

```

From the project root:
```

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

func start
```

You should see some text and a prompt: 

```
...
Select a number for worker runtime:
1. dotnet (isolated worker model)
2. dotnet (in-process model)
3. Node
4. Python
5. Powershell
6. Custom
Choose option: 
```

Choose `4` for Python.

You should now see a list of URLs for testing:

```
Functions:

	main: [GET] http://localhost:7071/home

	queryMissing_index: [GET] http://localhost:7071/query/missing_index

	queryNormal: [GET] http://localhost:7071/query/normal

	queryWait: [GET] http://localhost:7071/query/wait

For detailed output, run func with --verbose flag.
```

You may (will) need to install an ODBC driver in your dev instance to connect to DB

## Publish function to Azure

```
func azure functionapp publish [fa_name]
```

## When Finished Delete Resource Group
Don't forget this step! 
```
az group delete --name [resource_group_name]
```

## Troubleshooting

#### Terraform Apply Fails
- Verify: 
    - The Azure resources do not exist in Azure, sometimes a failed deploy can leave resources in an inconsistent state.
    - Ensure the subscription ID environment variable is populated and correct.

#### DB Admin Password
- Recommend not using `!` in the complex password as it requires escaping in shell commands.

#### Local Testing Not Working
- Ensure you have exported the DB name and password environment variables.
- To test locally, you must have an ODBC driver AND access to the MSSQL instance in Azure.
- To run again with different settings remove the file `local.settings.json`.

#### Publishing to Azure
- If this step fails, attemmpt without VPN (In my experience some VPNs interrupt this step).

#### Cannot Access After Deploy
- Some NATs can "float" between IP addresses. Ensure `my_ip_address_start` and `my_ip_address_end` cover the range of your outbound IP addresses.