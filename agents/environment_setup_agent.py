import autogen
from autogen_ext.tools.mcp import McpAgent

def create_environment_setup_agent(llm_config: dict) -> McpAgent:
    """Creates the agent responsible for infrastructure management."""
    return McpAgent(
        name="EnvironmentSetupAgent",
        llm_config=llm_config,
        system_message="""You are the Environment Setup Agent. Your role is to interact with the GCP infrastructure using the MCP server.
        Your primary tool is 'terraform_output' to fetch infrastructure details.
        When the user asks for infrastructure details, you must call the MCP server with the JSON: `{"tool": "terraform_output"}`.
        After receiving the output, summarize it and pass it to the SchemaConversionAgent.
        """,
        mcp_server_url="ws://localhost:8080",
    )