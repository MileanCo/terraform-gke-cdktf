#!/usr/bin/env python
from constructs import Construct
from cdktf import App, TerraformStack, TerraformVariable, TerraformOutput
from cdktf_cdktf_provider_google import provider, container_cluster, container_node_pool
import os


class GkeStack(TerraformStack):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # Configuration variables
        project_id = TerraformVariable(self, "project_id",
            type="string",
            description="The GCP project ID",
            default="your-project-id"
        )

        region = TerraformVariable(self, "region",
            type="string",
            description="The region to deploy resources",
            default="us-central1-a"
        )

        cluster_name = TerraformVariable(self, "cluster_name",
            type="string",
            description="The name of the GKE cluster",
            default="media-generator-cluster"
        )

        node_count = TerraformVariable(self, "node_count",
            type="number",
            description="Number of nodes in the default node pool",
            default=3
        )

        machine_type = TerraformVariable(self, "machine_type",
            type="string",
            description="Machine type for cluster nodes",
            default="e2-medium"
        )

        # Configure the Google Cloud Provider
        provider.GoogleProvider(self, "google",
            project=project_id.string_value,
            region=region.string_value
        )

        # Create the GKE cluster
        cluster = container_cluster.ContainerCluster(self, "gke_cluster",
            name=cluster_name.string_value,
            location=region.string_value,

            # We want to manage the node pool separately
            remove_default_node_pool=True,
            initial_node_count=1,

            # Enable network policy for security
            network_policy=container_cluster.ContainerClusterNetworkPolicy(
                enabled=True
            ),

            # Enable Workload Identity for secure pod authentication
            workload_identity_config=container_cluster.ContainerClusterWorkloadIdentityConfig(
                workload_pool=f"{project_id.string_value}.svc.id.goog"
            ),

            # Enable logging and monitoring
            logging_service="logging.googleapis.com/kubernetes",
            monitoring_service="monitoring.googleapis.com/kubernetes",

            # Deletion protection
            deletion_protection=False  # Set to True for production
        )

        # Create a managed node pool
        node_pool = container_node_pool.ContainerNodePool(self, "primary_nodes",
            name="primary-node-pool",
            location=region.string_value,
            cluster=cluster.name,
            node_count=node_count.number_value,

            node_config=container_node_pool.ContainerNodePoolNodeConfig(
                preemptible=True,  # Use preemptible instances for cost savings
                machine_type=machine_type.string_value,
                disk_size_gb=30,
                disk_type="pd-standard",

                # OAuth scopes for node permissions
                oauth_scopes=[
                    "https://www.googleapis.com/auth/logging.write",
                    "https://www.googleapis.com/auth/monitoring",
                    "https://www.googleapis.com/auth/devstorage.read_only",
                    "https://www.googleapis.com/auth/servicecontrol",
                    "https://www.googleapis.com/auth/service.management.readonly",
                    "https://www.googleapis.com/auth/trace.append"
                ],

                # Labels for resource management
                labels={
                    "env": "dev",
                    "project": "media-generator"
                },

                # Enable Workload Identity on nodes
                workload_metadata_config=container_node_pool.ContainerNodePoolNodeConfigWorkloadMetadataConfig(
                    mode="GKE_METADATA"
                )
            ),

            # Auto-scaling configuration
            autoscaling=container_node_pool.ContainerNodePoolAutoscaling(
                min_node_count=1,
                max_node_count=10
            ),

            # Auto-upgrade and auto-repair
            management=container_node_pool.ContainerNodePoolManagement(
                auto_repair=True,
                auto_upgrade=True
            )
        )

        # Outputs
        TerraformOutput(self, "cluster_name_output",
            value=cluster.name,
            description="The name of the GKE cluster"
        )

        TerraformOutput(self, "cluster_endpoint_output",
            value=cluster.endpoint,
            description="The endpoint of the GKE cluster"
        )

        TerraformOutput(self, "cluster_master_version_output",
            value=cluster.master_version,
            description="The master version of the GKE cluster"
        )


app = App()
GkeStack(app, "terraform-gke-cdktf")

app.synth()
