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
### Create Azure Resource Group and Function App with Terraform

This terraform code borrows from the Azure Functions Quickstart examples: https://learn.microsoft.com/en-us/azure/azure-functions/functions-get-started?pivots=programming-language-python

Copy `terraform.tvars.example` to `terraform.tvars` and edit to reflect your env:
```
# The admin password for the VM (SSH) and SQL Managed Instance.
# MUST be complex (e.g., "P@ssw0rd12345!")
admin_password   = "YourComplexSQLPassword123!"

# Your local public IP address. Find it by searching "what is my ip" in Google.
# This is required to secure access to the VM.
my_ip_address_start = ""
my_ip_address_end   = ""

# Details for New Relic instrumentation
new_relic_license_key        = "YOUR_INGEST_LICENSE_KEY"
new_relic_app_name           = "YOUR_APP_NAME"
```

Get Azure credentials: 
```
export ARM_SUBSCRIPTION_ID=$(az account show --query "id" --output tsv) 
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

This will run for a few minutes. When finsished, you should see an output similar to this:
```
admin_password = "complex_password_here_!23 "
asp_name = "vvwzuybj"
fa_name = "vvwzuybj"
fa_url = "https://vvwzuybj.azurewebsites.net"
resource_group_name = "rg-crisp-ostrich"
sa_name = "vvwzuybj"
sql_server_name = "sql-helped-rhino"
```
----

### Add the stored proceduures for the demo
This will download `sqlcmd` for your platform and run the  `stored_procedures.ql` file aginst the DB
```
../scripts/configuresql.sh
```
----
### Test locally
From the project root:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

func start
```

You may (will) need to install an ODBC driver in your dev instance to connect to DB

## Publish function to Azure

```
func azure functionapp publish [sa_name]
```
