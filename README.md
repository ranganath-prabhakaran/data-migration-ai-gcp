# Agent-Powered MySQL to Cloud SQL Migration on GCP

Welcome to the definitive, fully automated solution for migrating legacy MySQL databases to Google Cloud SQL. This project is orchestrated by a team of six specialized AI agents built using the AutoGen v0.6.1 framework.

The entire architecture is designed with a security-first mindset, operating within a private GCP network and leveraging the Model Context Protocol (MCP) for secure communication between agents and tools.

---

### Core Architecture

- AutoGen v0.6.1 & GraphFlow: Manages the complex, multi-step workflow between agents, ensuring proper sequencing, parallel execution, and error handling.
- Model Context Protocol (MCP): Acts as a secure, standardized API layer. The agents communicate with the "mcp_server" to execute tasks (like running Terraform or a schema check) without having direct access to the underlying shell or credentials.
- Secure GCP Environment:
    - Private Networking: All components (Cloud SQL, GCE VM) are deployed within a VPC with no public IP addresses. Access is handled securely via GCP's IAP (Identity-Aware Proxy).
    - Google Secret Manager: All secrets—database credentials, API keys—are stored and retrieved securely, never hardcoded or exposed in the environment.
- Gemini Flash LLM: Powers the agents' intelligence and decision-making capabilities.

---

### The Agent Team

1.  Environment Setup Agent: Provisions and manages the GCP infrastructure using Terraform via MCP calls.
2.  Schema Conversion Agent: Intelligently compares source and target schemas, identifies discrepancies, and generates/applies necessary DDL statements.
3.  Data Migration Agent: Dynamically determines the source database size and selects the optimal migration strategy (GCS Import, DMS, or MyDumper/MyLoader).
4.  Data Validation Agent: Performs post-migration integrity checks by comparing row counts and table checksums.
5.  Anomaly Detection Agent: Runs concurrently with the migration, monitoring logs in real-time to flag any errors or warnings.
6.  Performance Optimization Agent: After a successful migration, it analyzes the GCP resource utilization and provides actionable recommendations for rightsizing and cost savings.

---

### Step-by-Step Implementation Guide

#### 1. Prerequisites
- A GCP Project with Billing enabled.
- "gcloud" CLI installed and authenticated ("gcloud auth login", "gcloud config set project YOUR_PROJECT_ID").
- Terraform CLI installed locally.
- Python 3.10+ installed locally.

#### 2. Initial GCP Setup
Enable the necessary APIs for your project:
"""bash
gcloud services enable compute.googleapis.com sqladmin.googleapis.com servicenetworking.googleapis.com secretmanager.googleapis.com dms.googleapis.com cloudresourcemanager.googleapis.com iam.googleapis.com

Create a Service Account that the orchestrator VM will use:

Bash

gcloud iam service-accounts create migration-orchestrator-sa --display-name="Migration Orchestrator SA"

# Grant necessary roles (in production, these should be more granular)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID --member="serviceAccount:migration-orchestrator-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" --role="roles/owner"
3. Store All Secrets
Securely store your credentials in Secret Manager. The Service Account needs the Secret Manager Secret Accessor role.

Bash

# GCP Project ID where secrets are stored
gcloud secrets create gcp_project_id --replication-policy="automatic"
echo -n "your-gcp-project-id" | gcloud secrets versions add gcp_project_id --data-file=-

# Gemini API Key
gcloud secrets create gemini_api_key --replication-policy="automatic"
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets versions add gemini_api_key --data-file=-

# Legacy DB Credentials
gcloud secrets create legacy_db_host --replication-policy="automatic"
echo -n "YOUR_LEGACY_DB_IP" | gcloud secrets versions add legacy_db_host --data-file=-

gcloud secrets create legacy_db_user --replication-policy="automatic"
echo -n "your_legacy_db_user" | gcloud secrets versions add legacy_db_user --data-file=-

gcloud secrets create legacy_db_password --replication-policy="automatic"
echo -n "your_legacy_db_password" | gcloud secrets versions add legacy_db_password --data-file=-

gcloud secrets create legacy_db_name --replication-policy="automatic"
echo -n "your_legacy_db_name" | gcloud secrets versions add legacy_db_name --data-file=-

4. Deploy the Infrastructure
Clone this repository to your local machine. From the root directory, run the Terraform commands:

Bash

cd terraform/
terraform init
terraform plan -var="project_id=your-gcp-project-id"
terraform apply -var="project_id=your-gcp-project-id"
This will provision the VPC, the Cloud SQL instance, and the GCE VM that will act as the orchestrator.

5. Run the Migration
The setup_orchestrator.sh script automates the process of copying the code to the VM and starting the migration. Run it from your local machine's terminal:

Bash

chmod +x setup_orchestrator.sh
./setup_orchestrator.sh your-gcp-project-id

This script will:

Package the repository.

Use gcloud to copy the package to the orchestrator VM.

SSH into the VM and unpack the code.

Install all dependencies.

Start the mcp_server.py in the background.

Execute the main main.py script to kick off the agent workflow.

You can monitor the progress by viewing the migration.log file on the VM.