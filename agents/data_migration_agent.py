import autogen
from autogen_ext.tools.mcp import McpAgent

def create_data_migration_agent(llm_config: dict) -> McpAgent:
    """Creates the agent responsible for the actual data migration."""
    return McpAgent(
        name="DataMigrationAgent",
        llm_config=llm_config,
        system_message="""You are the Data Migration Agent. Your job is to move the data from the legacy database to Cloud SQL.
        First, you MUST determine the database size by calling the 'get_db_size' tool.
        Based on the returned size in GB, you will then call the appropriate migration tool:
        - '< 100GB': Use the 'migrate_gcs' tool.
        - '100GB to 500GB': Use the 'migrate_dms' tool.
        - '> 500GB': Use the 'migrate_mydumper' tool.
        You must clearly state which strategy you are choosing before executing.
        Upon completion, you will notify both the DataValidationAgent and the AnomalyDetectionAgent to proceed.
        """,
        mcp_server_url="ws://localhost:8080",
    )