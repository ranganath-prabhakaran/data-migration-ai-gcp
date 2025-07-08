output "orchestrator_vm_name" {
  description = "The name of the GCE VM that orchestrates the migration."
  value       = google_compute_instance.orchestrator_vm.name
}

output "orchestrator_vm_zone" {
  description = "The zone of the orchestrator VM, needed for SSH commands."
  value       = google_compute_instance.orchestrator_vm.zone
}

output "cloud_sql_instance_name" {
  description = "The name of the target Cloud SQL instance."
  value       = google_sql_database_instance.mysql_target.name
}

output "cloud_sql_private_ip" {
  description = "The private IP address of the Cloud SQL instance for internal connections."
  value       = google_sql_database_instance.mysql_target.private_ip_address
  sensitive   = true
}

output "vpc_network_name" {
  description = "The name of the VPC network created for the migration."
  value       = google_compute_network.migration_vpc.name
}