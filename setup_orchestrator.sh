#!/bin/bash

# This script sets up the migration orchestrator on the GCE VM.
# It should be run from your local machine after `terraform apply` is complete.

set -e # Exit immediately if a command exits with a non-zero status.

PROJECT_ID=$1
if [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 <your-gcp-project-id>"
    exit 1
fi

VM_NAME="migration-orchestrator-vm"
VM_ZONE="us-central1-a"
REPO_DIR="gcp-agentic-mysql-migration"
TAR_FILE="gcp-migration-code.tar.gz"

echo "--- Starting Orchestrator Setup for project: $PROJECT_ID ---"

# 1. Create a tarball of the repository, excluding unnecessary files.
echo "Step 1: Packaging the repository..."
tar --exclude-from=.gitignore --exclude='*.tar.gz' -czf $TAR_FILE .

# 2. Copy the tarball to the GCE instance.
echo "Step 2: Copying code to the orchestrator VM ($VM_NAME)..."
gcloud compute scp $TAR_FILE $VM_NAME:~/ --zone=$VM_ZONE --project=$PROJECT_ID

# 3. SSH into the VM and execute the setup commands.
echo "Step 3: Running remote setup on the VM..."
gcloud compute ssh $VM_NAME --zone=$VM_ZONE --project=$PROJECT_ID --command="
    set -e
    echo '--- On VM: Starting setup ---'

    # Update and install dependencies
    sudo apt-get update
    sudo apt-get install -y python3-venv python3-pip git

    # Unpack the code
    if [ -d '$REPO_DIR' ]; then
        rm -rf $REPO_DIR
    fi
    mkdir $REPO_DIR
    tar -xzf $TAR_FILE -C $REPO_DIR
    cd $REPO_DIR

    # Set up Python virtual environment and install requirements
    echo '--- On VM: Setting up Python environment ---'
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

    # Start the MCP server in the background
    echo '--- On VM: Starting MCP Server in background ---'
    nohup python mcp/mcp_server.py > mcp.log 2>&1 &
    sleep 5 # Give it a moment to start up

    # Run the main orchestration script
    echo '--- On VM: Starting main migration orchestrator ---'
    python main.py > migration.log 2>&1

    echo '--- On VM: Orchestration script has finished executing. ---'
"

echo "--- Orchestrator Setup Complete. Monitor logs on the VM. ---"