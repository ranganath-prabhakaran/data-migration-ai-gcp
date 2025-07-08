import http.server
import socketserver
import json
import threading
import subprocess
import mysql.connector
import os
from autogen_ext.tools.mcp import McpWorkbench, StdioMcpToolAdapter
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# Note: This script requires the following Python libraries:
# pip install google-cloud-secret-manager mysql-connector-python
from google.cloud import secretmanager

# --- Configuration Loading ---

def get_secret(project_id, secret_id, version_id="latest"):
    """Fetches a secret from GCP Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Failed to access secret: {secret_id} in project: {project_id}. Error: {e}")
        raise

def load_terraform_output(filename):
    """Reads a value from a terraform output file in the parent directory."""
    # This script is in 'mcp/', terraform outputs are in 'terraform_outputs/'
    path = os.path.join(os.path.dirname(__file__), '..', 'terraform_outputs', filename)
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Error: Terraform output file not found at {path}.")
        print("Please ensure 'terraform apply' and 'setup_orchestrator.sh' ran successfully.")
        raise
    except Exception as e:
        print(f"Error reading terraform file {path}. Error: {e}")
        raise

def load_app_configuration():
    """
    Loads all necessary configuration from Terraform outputs and Secret Manager
    at server startup.
    """
    config = {}
    print("Loading application configuration...")
    try:
        # 1. Load non-sensitive resource info from Terraform state
        config['project_id'] = load_terraform_output('project_id.txt')
        config['cloud_sql_connection_name'] = load_terraform_output('cloud_sql_connection_name.txt')
        config['dms_job_name'] = load_terraform_output('dms_job_name.txt')
        config['dms_job_region'] = load_terraform_output('dms_job_region.txt')

        # 2. Load sensitive data from Secret Manager using the project_id
        print(f"Fetching secrets from project: {config['project_id']}...")
        config['legacy_db_host'] = get_secret(config['project_id'], 'legacy_db_host')
        config['legacy_db_user'] = get_secret(config['project_id'], 'legacy_db_user')
        config['legacy_db_password'] = get_secret(config['project_id'], 'legacy_db_password')
        config['legacy_db_name'] = get_secret(config['project_id'], 'legacy_db_name')
        config['cloud_sql_user'] = get_secret(config['project_id'], 'cloud_sql_user')
        config['cloud_sql_password'] = get_secret(config['project_id'], 'cloud_sql_password')

        print("Configuration loaded successfully.")
        return config
    except Exception as e:
        print(f"CRITICAL: Failed to load configuration. Server cannot start. Error: {e}")
        # In a real-world scenario, you might have more sophisticated error handling
        exit(1)

# --- Database & Cloud Tool Implementation ---

def get_db_connection(config, use_source=True):
    """
    Establishes a connection to the source (MySQL) or target (Cloud SQL) database.
    """
    try:
        if use_source:
            # Connect to the source database
            return mysql.connector.connect(
                host=config['legacy_db_host'],
                user=config['legacy_db_user'],
                password=config['legacy_db_password'],
                database=config['legacy_db_name']
            )
        else:
            # Connect to Cloud SQL via the Auth Proxy's Unix socket
            # This is the recommended and most secure method for GCE/GKE
            return mysql.connector.connect(
                user=config['cloud_sql_user'],
                password=config['cloud_sql_password'],
                database=config['legacy_db_name'], # Assuming same DB name
                unix_socket=f"/cloudsql/{config['cloud_sql_connection_name']}"
            )
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def get_db_size(config):
    """Calculates the size of the source database in GB."""
    conn = get_db_connection(config, use_source=True)
    if not conn:
        return "Error: Could not connect to the source database."
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(data_length + index_length) / 1024 / 1024 / 1024
            FROM information_schema.tables WHERE table_schema = %s
        """, (config['legacy_db_name'],))
        result = cursor.fetchone()
        size_gb = result[0] if result and result[0] is not None else 0
        return f"{size_gb:.2f}GB"
    except mysql.connector.Error as err:
        return f"Error executing query to get DB size: {err}"
    finally:
        if conn and conn.is_connected():
            conn.close()

def run_gcloud_command(command):
    """Executes a gcloud command and returns its output."""
    try:
        print(f"Executing command: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_message = f"Error executing gcloud command: {e.stderr.strip()}"
        print(error_message)
        return error_message

def migrate_dms(config):
    """Starts the pre-configured Database Migration Service (DMS) job."""
    command = [
        "gcloud", "dms", "jobs", "start", config['dms_job_name'],
        f"--project={config['project_id']}",
        f"--region={config['dms_job_region']}"
    ]
    return run_gcloud_command(command)

def get_table_property(config, table_name, is_checksum=False):
    """Gets row count or checksum for a table from both databases."""
    prop_name = "Checksum" if is_checksum else "Row Count"
    source_conn = get_db_connection(config, use_source=True)
    target_conn = get_db_connection(config, use_source=False)

    if not source_conn or not target_conn:
        return f"Error: Could not connect to one or both databases for {prop_name} validation."

    try:
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        query = f"CHECKSUM TABLE {table_name}" if is_checksum else f"SELECT COUNT(*) FROM {table_name}"

        source_cursor.execute(query)
        source_result = source_cursor.fetchone()[1 if is_checksum else 0]

        target_cursor.execute(query)
        target_result = target_cursor.fetchone()[1 if is_checksum else 0]

        return json.dumps({
            "table": table_name,
            "property": prop_name,
            "source_value": str(source_result),
            "target_value": str(target_result),
            "match": source_result == target_result
        })

    except mysql.connector.Error as err:
        return f"Error validating {prop_name} for table {table_name}: {err}"
    finally:
        if source_conn and source_conn.is_connected():
            source_conn.close()
        if target_conn and target_conn.is_connected():
            target_conn.close()

# --- MCP Server ---

class MCPRequestHandler(BaseHTTPRequestHandler):
    # Class-level attribute to hold the config, loaded once at server start
    server_config = None

    def do_GET(self):
        if self.path == '/healthz':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'ok')
        else:
            self.send_error(404, 'File Not Found')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            request_data = json.loads(post_data)
            print(f"Received request: {request_data}")
            response_data = self.handle_request(request_data)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_error(500, "Internal Server Error")

    def handle_request(self, request_data):
        tool_code = request_data.get('tool_code', '')
        # Basic parsing to extract tool name and arguments
        try:
            tool_name = tool_code.split('(')[0].replace('print(','').strip()
            args_str = tool_code[tool_code.find('(')+1:tool_code.rfind(')')]
            args = [a.strip().replace('"', '').replace("'", "") for a in args_str.split(',') if a]
        except IndexError:
            return {"output": "Error: Invalid tool_code format"}

        print(f"Executing tool '{tool_name}' with args {args}")
        output = self.main_tool_handler(tool_name, args, self.server_config)
        return {"output": output}

    def main_tool_handler(self, tool_name, args, config):
        """Routes tool calls to the appropriate Python function."""
        # Database readiness tools
        if tool_name == "get_db_size":
            return get_db_size(config)
        # Migration tools
        elif tool_name == "migrate_dms":
            return migrate_dms(config)
        # Validation tools
        elif tool_name == "get_row_count":
            return get_table_property(config, args[0], is_checksum=False) if args else "Error: table_name required."
        elif tool_name == "checksum_table":
            return get_table_property(config, args[0], is_checksum=True) if args else "Error: table_name required."
        # Fallback for unimplemented tools
        elif tool_name in ["compare_schema", "migrate_gcs", "migrate_mydumper"]:
             return f"Tool '{tool_name}' is a valid placeholder but not implemented in this version."
        else:
            return f"Error: Tool '{tool_name}' is not recognized."

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

if __name__ == '__main__':
    # Load configuration once globally at server startup.
    # The handler will access this via its class attribute.
    MCPRequestHandler.server_config = load_app_configuration()

    port = 8000
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, MCPRequestHandler)
    print(f"Starting MCP server on http://localhost:{port}...")
    httpd.serve_forever()