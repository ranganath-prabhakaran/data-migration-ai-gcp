provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_compute_network" "migration_vpc" {
  project                 = var.project_id
  name                    = "agentic-migration-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "orchestrator_subnet" {
  project       = var.project_id
  name          = "orchestrator-subnet"
  ip_cidr_range = "10.20.0.0/24"
  region        = var.region
  network       = google_compute_network.migration_vpc.id
}

resource "google_compute_global_address" "private_ip_for_sql" {
  project       = var.project_id
  name          = "private-ip-for-sql-peering"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.migration_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.migration_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_for_sql.name]
}

resource "google_sql_database_instance" "mysql_target" {
  project          = var.project_id
  name             = "mysql-agentic-migration-target"
  database_version = "MYSQL_8_0"
  region           = var.region
  settings {
    tier = var.db_machine_type
    ip_configuration {
      ipv4_enabled    = false # No public IP
      private_network = google_compute_network.migration_vpc.id
    }
    backup_configuration {
      enabled = true
    }
    availability_type = "REGIONAL"
  }
  deletion_protection = false # Set to 'true' for production
  depends_on          = [google_service_networking_connection.private_vpc_connection]
}

resource "google_compute_instance" "orchestrator_vm" {
  project      = var.project_id
  zone         = var.zone
  name         = "migration-orchestrator-vm"
  machine_type = "e2-medium"
  tags         = ["orchestrator-vm", "allow-iap-ssh"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network    = google_compute_network.migration_vpc.id
    subnetwork = google_compute_subnetwork.orchestrator_subnet.id
    # No public IP address is assigned by default
  }

  service_account {
    email  = "migration-orchestrator-sa@${var.project_id}.iam.gserviceaccount.com"
    scopes = ["cloud-platform"]
  }

  metadata = {
    # Allows a startup script to be passed via gcloud or other tools
    enable-oslogin = "TRUE"
  }
}

# Securely allow SSH via Google's Identity-Aware Proxy, not a public firewall rule.
resource "google_compute_firewall" "allow_iap_ssh" {
  project = var.project_id
  name    = "allow-ssh-via-iap"
  network = google_compute_network.migration_vpc.name
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  # This is Google's IP range for the IAP service
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["allow-iap-ssh"]
}