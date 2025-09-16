#!/bin/bash

# Script to generate a dedicated kubeconfig file for your GKE cluster
# Usage: ./generate-kubeconfig.sh

set -e

echo "🔧 Generating kubeconfig for GKE cluster..."

# Get cluster details from CDKTF outputs and terraform.tfvars
CLUSTER_NAME=$(cdktf output terraform-gke-cdktf | grep cluster_name_output | cut -d'=' -f2 | xargs)
REGION=$(grep 'region.*=' terraform.tfvars | cut -d'"' -f2)
PROJECT_ID=$(grep 'project_id.*=' terraform.tfvars | cut -d'"' -f2)

echo "📋 Cluster Details:"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Cluster: $CLUSTER_NAME"

# Create kubeconfig file
KUBECONFIG_FILE="./kubeconfig-${CLUSTER_NAME}"

echo "📝 Generating kubeconfig file: $KUBECONFIG_FILE"

# Generate the kubeconfig using gcloud
KUBECONFIG="$PWD/$KUBECONFIG_FILE" gcloud container clusters get-credentials "$CLUSTER_NAME" \
  --region "$REGION" \
  --project "$PROJECT_ID"

echo "✅ Kubeconfig generated successfully!"
echo ""
echo "🚀 To use this kubeconfig:"
echo "   export KUBECONFIG=$PWD/$KUBECONFIG_FILE"
echo "   export PATH=\$PATH:/usr/local/share/google-cloud-sdk/bin"
echo "   kubectl get nodes"
echo ""
echo "💡 Or use it directly:"
echo "   PATH=\$PATH:/usr/local/share/google-cloud-sdk/bin kubectl --kubeconfig=$KUBECONFIG_FILE get nodes"
echo ""
echo "📁 Kubeconfig saved to: $KUBECONFIG_FILE"

# Create a convenience script
cat > kubectl-gke.sh << 'EOF'
#!/bin/bash
# Convenience script to use kubectl with the GKE cluster
export PATH=$PATH:/usr/local/share/google-cloud-sdk/bin
exec kubectl --kubeconfig=./kubeconfig-media-generator-cluster "$@"
EOF

chmod +x kubectl-gke.sh
echo ""
echo "🎯 Convenience script created: ./kubectl-gke.sh"
echo "   Usage: ./kubectl-gke.sh get nodes"
echo "   Usage: ./kubectl-gke.sh get pods"
