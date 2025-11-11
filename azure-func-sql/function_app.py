import newrelic.agent
import azure.functions as func
import datetime
import json
import logging
import os
import pyodbc

newrelic.agent.initialize()
app_name = os.environ.get(
    "NEW_RELIC_APP_NAME", os.environ.get("NEW_RELIC_APP_NAME", None)
)
newrelic.agent.register_application(app_name)

app = func.FunctionApp()


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# --- Database Configuration ---
DB_SERVER = os.environ.get('DB_SERVER', 'rg-lion.database.windows.net') # Use the service name from docker-compose
DB_DATABASE = os.environ.get('DB_DATABASE', 'AdventureWorks')
DB_USERNAME = os.environ.get('DB_USERNAME', 'azureadmin')
MSSQL_SA_PASSWORD = os.environ.get('MSSQL_SA_PASSWORD', 'complex_password_here_!23')
DB_SERVER = DB_SERVER+".database.windows.net"

def get_db_connection():
    """Establishes a connection to the SQL Server database."""
    connection_string = (
        f'DRIVER={{ODBC Driver 18 for SQL Server}};'
        f'SERVER={DB_SERVER};'
        f'DATABASE={DB_DATABASE};'
        f'UID={DB_USERNAME};'
        f'PWD={MSSQL_SA_PASSWORD};'
        f'TrustServerCertificate=yes;' # Necessary for self-signed certs in Docker
    )
    try:
        logging.info(f"Attempting to connect to {DB_DATABASE} on {DB_SERVER} with {DB_USERNAME} user...")
        cnxn = pyodbc.connect(connection_string, autocommit=True)
        logging.info("Database connection successful.")
        return cnxn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        logging.error(f"Database connection failed: {sqlstate}")
        raise

def execute_query(proc_name, params=()):
    """Executes a stored procedure and returns the results as a JSON string."""
    cnxn = None
    try:
        cnxn = get_db_connection()
        cursor = cnxn.cursor()
        
        # Construct the full stored procedure call
        # The placeholder '?' is standard for pyodbc
        param_placeholders = ','.join(['?'] * len(params))
        sql_query = f"{{CALL {proc_name}({param_placeholders})}}"

        logging.info(f"Executing stored procedure: {proc_name} with params: {params}")
        
        # pyodbc expects params as a tuple, even for a single param
        if isinstance(params, (str, int)):
            params = (params,)

        cursor.execute(sql_query, params)

        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        
        return results

    except pyodbc.Error as e:
        logging.error(f"Error executing query {proc_name}: {e}")
        return ({"error": f"Database error: {e}"})
    finally:
        if cnxn:
            cnxn.close()
            logging.info("Database connection closed.")

# @app.function_name(name="RootFunction")
@app.route(route="home", methods=["GET"])
def main(req: func.HttpRequest) -> func.HttpResponse:
    function_directory = os.path.dirname(__file__)
    html_file_path = os.path.join(function_directory, "static", "index.html")
    logging.info(f"processing main")

    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        return func.HttpResponse(body=html_content, 
                                headers={"Content-Type": "text/html"},
                                status_code=200)

@app.route(route="query/normal", methods=["GET"])
def queryNormal(req: func.HttpRequest):
    logging.info(f"processing /query/normal")
    customer_id = 29847
    rv = execute_query('GetRecentCustomerOrders', (customer_id,))
    logging.info(f"rv: {rv}")
    json_string = json.dumps(rv,  default=str)
    return func.HttpResponse(body=json_string,
                                headers={'Content-Type': 'json'})

@app.route(route="query/wait", methods=["GET"])
def queryWait(req: func.HttpRequest):
    logging.info(f"processing /query/wait")
    rv = execute_query('GenerateSlowSummaryReport')
    json_string = json.dumps(rv, default=str)
    return func.HttpResponse(body=json_string,
                                headers={'Content-Type': 'json'})                                

@app.route(route="query/missing_index", methods=["GET"])
def queryMissing_index(req: func.HttpRequest):
    logging.info(f"processing /query/missing_index")
    rv = execute_query('FindPersonByLastName', (last_name,))
    json_string = json.dumps(rv, default=str)
    return func.HttpResponse(body=json_string,
                                headers={'Content-Type': 'json'})        
