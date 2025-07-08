import http.server
import socketserver
import json
import threading
import subprocess
from autogen_ext.tools.mcp import McpWorkbench, StdioMcpToolAdapter

# --- Tool Definitions ---
# In a real application, these would be more robust scripts.
# For this self-contained example, we define them as simple command-line executions.

def run_tool(command):
    """Runs a command and captures its output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return json.dumps({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return json.dumps({"status": "error", "message": e.stderr})

def main_tool_handler():
    """
    Reads a JSON request from stdin, determines the tool to run, and prints the result to stdout.
    This single script acts as the entry point for all tools called by StdioMcpToolAdapter.
    """
    try:
        request_str = input()
        request = json.loads(request_str)
        tool_name = request.get("tool")

        # This is where you would map tool names to actual functions or scripts
        if tool_name == "terraform_output":
            # Assuming terraform is in the PATH and this script is run from the repo root
            command = "cd terraform && terraform output -json"
            output = run_tool(command)
        elif tool_name == "compare_schema":
            output = json.dumps({"status": "success", "output": "Schemas are compatible. No changes needed."})
        elif tool_name == "get_db_size":
            # Simulate a medium-sized DB to trigger the DMS strategy
            output = json.dumps({"status": "success", "output": {"size_gb": 250}})
        elif tool_name == "migrate_dms":
            output = json.dumps({"status": "success", "output": "DMS migration job started and completed successfully."})
        elif tool_name == "validate_row_counts":
            output = json.dumps({"status": "success", "output": "Row counts match between source and target."})
        elif tool_name == "validate_checksums":
            output = json.dumps({"status": "success", "output": "Checksums match for all tables."})
        elif tool_name == "monitor_logs":
            output = json.dumps({"status": "success", "output": "No anomalies detected in logs."})
        elif tool_name == "analyze_performance":
            recommendation = "CPU utilization is stable at 45%. Current instance size is appropriate. No changes recommended at this time."
            output = json.dumps({"status": "success", "output": recommendation})
        else:
            output = json.dumps({"status": "error", "message": f"Unknown tool: {tool_name}"})

        print(output)

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

# --- Server Setup ---

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/healthz':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")

def run_health_check_server(port):
    with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
        print(f"Health check server running on port {port}")
        httpd.serve_forever()

if __name__ == "__main__":
    # If the script is called with 'tool_handler' argument, it runs the tool logic
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'tool_handler':
        main_tool_handler()
    else:
        # Otherwise, it starts the MCP server
        print("Initializing MCP Server...")
        mcp_port = 8080
        health_port = 8081

        health_thread = threading.Thread(target=run_health_check_server, args=(health_port,), daemon=True)
        health_thread.start()
        
        # All tools will call this script itself with the 'tool_handler' argument
        command_to_run_tool = f"python3 mcp/mcp_server.py tool_handler"

        tools = {
            # Each tool is an instance of the StdioMcpToolAdapter pointing to our handler
            tool_name: StdioMcpToolAdapter(name=tool_name, command=command_to_run_tool)
            for tool_name in [
                "terraform_output", "compare_schema", "get_db_size",
                "migrate_dms", "migrate_gcs", "migrate_mydumper",
                "validate_row_counts", "validate_checksums",
                "monitor_logs", "analyze_performance"
            ]
        }

        try:
            with McpWorkbench(tools, host="0.0.0.0", port=mcp_port) as workbench:
                print(f"MCP Workbench is running on port {mcp_port}. Waiting for agent connections...")
                workbench.run()
        except KeyboardInterrupt:
            print("\nShutting down MCP Server.")