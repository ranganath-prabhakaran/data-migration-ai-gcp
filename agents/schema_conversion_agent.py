import autogen
from autogen_ext.tools.mcp import McpAgent

def create_schema_conversion_agent(llm_config: dict) -> McpAgent:
    """Creates the agent responsible for schema analysis and conversion."""
    return McpAgent(
        name="SchemaConversionAgent",
        llm_config=llm_config,
        system_message="""You are the Schema Conversion Agent. You receive infrastructure details and are responsible for comparing the source and target database schemas.
        You must use the 'compare_schema' tool via the MCP server.
        Formulate a JSON request `{"tool": "compare_schema"}` and send it.
        If there are discrepancies, report them. If the schemas are compatible, confirm and pass control to the DataMigrationAgent.
        If the target schema needs creation, use the 'create_schema' tool.
        """,
        mcp_server_url="ws://localhost:8080",
    )