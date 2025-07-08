import autogen
from autogen_ext.tools.mcp import McpAgent

def create_anomaly_detection_agent(llm_config: dict) -> McpAgent:
    """Creates the agent that monitors logs during migration."""
    return McpAgent(
        name="AnomalyDetectionAgent",
        llm_config=llm_config,
        system_message="""You are the Anomaly Detection Agent. You are the vigilant watchdog of the migration process.
        You run concurrently with the DataMigrationAgent.
        Your one job is to repeatedly call the 'monitor_logs' tool via the MCP server.
        If the tool returns any anomalies (errors, warnings, failures), you must immediately interrupt the flow and report the issue with high severity.
        If no anomalies are found after the migration agent is finished, you will report "All clear" to the DataValidationAgent.
        """,
        mcp_server_url="ws://localhost:8080",
    )