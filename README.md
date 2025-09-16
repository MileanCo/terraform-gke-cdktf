# Terraform CDK for GKE

This project uses CDK for Terraform (CDKTF) with Python to provision a Google Kubernetes Engine (GKE) cluster.

## Prerequisites

1. **Google Cloud SDK**: Install and configure `gcloud`
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL

   # Login and set project
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   gcloud auth application-default login
   ```

2. **Enable required APIs**:
   ```bash
   gcloud services enable container.googleapis.com
   gcloud services enable compute.googleapis.com
   ```

## Project Setup

1. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   # or
   pipenv shell
   ```

2. **Update configuration**:
   Edit `terraform.tfvars` with your project details:
   ```hcl
   project_id = "your-actual-project-id"
   region = "us-central1-a"
   cluster_name = "your-cluster-name"
   node_count = 3
   machine_type = "e2-medium"
   ```

## Commands

### Standard CDKTF Workflow
```bash
# Activate virtual environment first
source .venv/bin/activate

# Synthesize (Generate Terraform files)
cdktf synth

# Plan (See what will be created)
cdktf diff

# Deploy
cdktf deploy

# Get outputs
cdktf output

# Destroy
cdktf destroy
```

## What This Creates

- **GKE Cluster**: A managed Kubernetes cluster
- **Node Pool**: Auto-scaling node pool with preemptible instances
- **Security Features**:
  - Network policy enabled
  - Workload Identity configured
  - Proper OAuth scopes
- **Monitoring**: Logging and monitoring enabled
- **Auto-management**: Auto-repair and auto-upgrade enabled

## Connecting to Your Cluster

After deployment, generate a dedicated kubeconfig file:

### Option 1: Use the convenience script (Recommended)
```bash
# Generate kubeconfig and convenience script
./generate-kubeconfig.sh

kubectl get nodes --kubeconfig ./kubeconfig-media-generator-cluster
kubectl get services
```

## Deploying Applications

After your GKE cluster is running, you need to build and deploy your application:

### 1. Build and Push Docker Image

First, build your application Docker image:

```bash
# Navigate to the examples directory
cd examples

# Build the Docker image
docker build -t gcr.io/generator-471213/media-generator:latest .

# Configure Docker to authenticate with Google Container Registry
gcloud auth configure-docker

# Push the image to GCR
docker push gcr.io/generator-471213/media-generator:latest

# Go back to the main directory
cd ..
```

### 2. Install Helm
```bash
brew install helm
```

### 3. Deploy with Helm
```bash
# Make sure you're using the correct kubeconfig
export KUBECONFIG=./kubeconfig-media-generator-cluster

# Deploy the application
helm install media-generator ./helm-charts/media-generator-simple
```

### 4. Check Deployment
```bash
# Check what was deployed
helm list

# Check Kubernetes resources
./kubectl-gke.sh get pods
./kubectl-gke.sh get services

# Watch pods come online
./kubectl-gke.sh get pods -w
```

### 5. Test Your Application
```bash
# Get the external IP (may take a few minutes)
./kubectl-gke.sh get services

# Test the endpoints (replace EXTERNAL_IP with actual IP)
curl http://EXTERNAL_IP/
curl http://EXTERNAL_IP/health
curl http://EXTERNAL_IP/api/media
```

See `helm-charts/README.md` for detailed deployment instructions.

## Cost Optimization

- Uses preemptible instances for cost savings
- Auto-scaling from 1 to 10 nodes
- Standard persistent disks instead of SSD

## Security

- Workload Identity enabled for secure pod authentication
- Network policies enabled
- Proper OAuth scopes configured
- Auto-repair and auto-upgrade enabled
