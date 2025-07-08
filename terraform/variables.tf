variable "project_id" {
  description = "The GCP Project ID where resources will be deployed."
  type        = string
}

variable "region" {
  description = "The GCP region for deploying resources."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone for the orchestrator VM."
  type        = string
  default     = "us-central1-a"
}

variable "db_machine_type" {
  description = "The machine type for the Cloud SQL instance (e.g., db-n1-standard-2)."
  type        = string
  default     = "db-n1-standard-2"
}