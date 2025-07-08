#### `main.py`

import autogen
from autogen.graph_utils import DiGraphBuilder
import json
import time
import requests
from agents.environment_setup_agent import create_environment_setup_agent
from agents.schema_conversion_agent import create_schema_conversion_agent
from agents.data_migration_agent import create_data_migration_agent
from agents.data_validation_agent import create_data_validation_agent
from agents.anomaly_detection_agent import create_anomaly_detection_agent
from agents.performance_optimization_agent import create_performance_optimization_agent
from tools.gemini_client import GeminiClient
from tools.secret_manager import SecretManager

def main():
    """
    The main orchestration function that sets up and runs the agentic workflow.
    """
    print("--- Initializing Migration Orchestrator ---")

    # Initialize secret manager to fetch configuration
    secret_manager = SecretManager()
    project_id = secret_manager.get_secret("gcp_project_id")
    if not project_id:
        raise ValueError("GCP_PROJECT_ID not found in Secret Manager.")

    # Initialize the LLM client
    gemini_client = GeminiClient(secret_manager)
    llm_config = {"llm": gemini_client}

    print(f"Project ID loaded: {project_id}")
    print("Checking MCP Server health...")

    # Health check for MCP server before starting
    try:
        response = requests.get("http://localhost:8081/healthz", timeout=10)
        if response.status_code != 200:
            print(f"MCP Server health check failed: {response.text}")
            return
        print("MCP Server is healthy. Proceeding...")
    except requests.ConnectionError as e:
        print(f"Failed to connect to MCP Server: {e}. Is it running?")
        return

    # Create all the agents
    env_agent = create_environment_setup_agent(llm_config)
    schema_agent = create_schema_conversion_agent(llm_config)
    migration_agent = create_data_migration_agent(llm_config)
    validation_agent = create_data_validation_agent(llm_config)
    anomaly_agent = create_anomaly_detection_agent(llm_config)
    perf_agent = create_performance_optimization_agent(llm_config)
    
    # User proxy to manage the conversation flow
    user_proxy = autogen.UserProxyAgent(
        name="UserProxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1, # The graph controls the flow
        is_termination_msg=lambda x: "completed and validated" in x.get("content", "").lower(),
        code_execution_config=False,
    )

    # Define the workflow using GraphFlow
    graph = DiGraphBuilder(
        participants=[user_proxy, env_agent, schema_agent, migration_agent, validation_agent, anomaly_agent, perf_agent]
    )

    # Define the sequence and dependencies
    graph.add_edge(user_proxy, env_agent)
    graph.add_edge(env_agent, schema_agent)
    graph.add_edge(schema_agent, migration_agent)
    
    # Anomaly detection runs in parallel with migration
    graph.add_edge(migration_agent, anomaly_agent)
    
    # Validation happens after migration
    graph.add_edge(migration_agent, validation_agent)
    
    # Anomaly detection must also finish before validation
    graph.add_edge(anomaly_agent, validation_agent)

    # Performance optimization is the final step
    graph.add_edge(validation_agent, perf_agent)
    graph.add_edge(perf_agent, user_proxy) # Report back to proxy

    workflow = graph.build()
    print("--- Workflow Graph Built Successfully ---")

    # Initial message to kick off the workflow
    initial_prompt = f"""
    The migration process for project '{project_id}' is ready to begin.
    
    Your first task, EnvironmentSetupAgent, is to call the 'terraform_output' tool via the MCP server to get the details of our provisioned infrastructure. This information will be used by subsequent agents.
    
    The MCP tool expects a JSON payload like: {{"tool": "terraform_output"}}
    """
    
    # Initiate the chat
    user_proxy.initiate_chat(
        recipient=workflow,
        message=initial_prompt
    )

    print("--- Migration Workflow Complete ---")

if __name__ == "__main__":
    main()