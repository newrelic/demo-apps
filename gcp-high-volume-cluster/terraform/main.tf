terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  credentials = file("${path.module}/service-account-key.json")
  project     = var.project_id
  region      = var.region
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "gke-network"
  auto_create_subnetworks = false
}

# Subnetwork for GKE cluster
resource "google_compute_subnetwork" "subnet" {
  name                     = "gke-subnet"
  ip_cidr_range            = "10.0.0.0/24"
  region                   = var.region
  network                  = google_compute_network.vpc.id
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

# Cloud Router for Cloud NAT
resource "google_compute_router" "router" {
  name    = "gke-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

# Cloud NAT for private nodes to access internet
resource "google_compute_router_nat" "nat" {
  name                               = "gke-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

resource "google_container_cluster" "primary" {
  name               = "gcp-high-volume-cluster"
  location           = var.region
  network            = google_compute_network.vpc.id
  subnetwork         = google_compute_subnetwork.subnet.id
  deletion_protection = false

  # Standard mode (not Autopilot)
  initial_node_count       = 1
  remove_default_node_pool = true

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

resource "google_container_node_pool" "primary_nodes" {
  name       = "primary-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = 3

  autoscaling {
    min_node_count = 3
    max_node_count = 20
  }

  node_config {
    machine_type = "n1-standard-4"
    disk_size_gb = 100

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      env = "prod"
    }

    tags = ["gke-node", "high-volume"]
  }
}

output "cluster_name" {
  value       = google_container_cluster.primary.name
  description = "GKE cluster name"
}

output "cluster_endpoint" {
  value       = google_container_cluster.primary.endpoint
  description = "GKE cluster endpoint"
  sensitive   = true
}

output "cluster_ca_certificate" {
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  description = "GKE cluster CA certificate"
  sensitive   = true
}
