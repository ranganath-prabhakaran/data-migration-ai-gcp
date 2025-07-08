import autogen
from autogen_ext.tools.mcp import McpAgent

def create_performance_optimization_agent(llm_config: dict) -> McpAgent:
    """Creates the agent that provides post-migration optimization recommendations."""
    return McpAgent(
        name="PerformanceOptimizationAgent",
        llm_config=llm_config,
        system_message="""You are the Performance Optimization Agent. You are the final step in the process.
        After a successful and validated migration, your task is to analyze the performance of the newly created GCP infrastructure.
        You must call the 'analyze_performance' tool via the MCP server.
        Based on the output (CPU, memory usage, etc.), you will provide a clear, actionable list of recommendations.
        For example, 'Consider downsizing Cloud SQL instance from n1-standard-2 to n1-standard-1 to save costs' or 'CPU utilization is high, consider upgrading the instance tier.'
        Your report marks the end of the migration process.
        """,
        mcp_server_url="ws://localhost:8080",
    )