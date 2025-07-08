import autogen
from autogen_ext.tools.mcp import McpAgent

def create_data_validation_agent(llm_config: dict) -> McpAgent:
    """Creates the agent responsible for post-migration data validation."""
    return McpAgent(
        name="DataValidationAgent",
        llm_config=llm_config,
        system_message="""You are the Data Validation Agent. Your task is to verify the integrity of the migration.
        You will be activated after the DataMigrationAgent completes its work.
        You must use two tools via the MCP server: 'validate_row_counts' and 'validate_checksums'.
        Execute them sequentially.
        Compile a final validation report. If everything matches, declare the migration a success. If not, flag the discrepancies clearly.
        Finally, pass control to the PerformanceOptimizationAgent.
        """,
        mcp_server_url="ws://localhost:8080",
    )