# Sample Application for GKE

This directory contains a sample Flask application that demonstrates how to containerize and deploy applications to your GKE cluster using modern, industry-standard tools.

## Summary of Changes Made

We've moved away from custom scripts to industry-standard tools:

- ❌ **Removed**: Custom `deploy_app.py` script (unnecessary complexity)
- ✅ **Added**: Standard Docker + Helm deployment workflow
- ✅ **Added**: Proper Helm chart structure in `../helm-charts/media-generator-simple/`
- ✅ **Added**: Environment-specific configuration support
- ✅ **Added**: Dedicated kubeconfig management with `../generate-kubeconfig.sh`

## Modern Deployment Workflow

### 1. Build and Push Docker Image

```bash
# Build the Docker image
docker build -t gcr.io/generator-471213/media-generator:latest .

# Configure Docker for Google Container Registry
gcloud auth configure-docker

# Push the image
docker push gcr.io/generator-471213/media-generator:latest
```

### 2. Deploy with Helm (Industry Standard)

```bash
# Go back to the main terraform-gke-cdktf directory
cd ..

# Make sure you're connected to your cluster
./generate-kubeconfig.sh  # Generate kubeconfig if needed
export KUBECONFIG=./kubeconfig-media-generator-cluster

# Deploy using Helm
helm install media-generator ./helm-charts/media-generator-simple

# Check deployment status
./kubectl-gke.sh get pods
./kubectl-gke.sh get services
```

## Testing the Application

### Check Deployment Status
```bash
# View all resources
./kubectl-gke.sh get all

# Check Helm releases
helm list

# Get service details
./kubectl-gke.sh get services
```

### Test the Endpoints
```bash
# Get the external IP (may take a few minutes to provision)
./kubectl-gke.sh get services

# Test endpoints (replace EXTERNAL_IP with actual IP)
curl http://EXTERNAL_IP/
curl http://EXTERNAL_IP/health
curl http://EXTERNAL_IP/api/media
```

## Local Development

Test locally before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app locally
python sample_flask_app.py

# Test endpoints
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/api/media
```

## Application Management

### Update Your Application
```bash
# Build new version
docker build -t gcr.io/generator-471213/media-generator:v1.1 .
docker push gcr.io/generator-471213/media-generator:v1.1

# Update values.yaml with new tag
# Then upgrade with Helm
helm upgrade media-generator ./helm-charts/media-generator-simple
```

### Remove Application
```bash
helm uninstall media-generator
```

### View Logs
```bash
./kubectl-gke.sh logs -l app=media-generator
```

## What This Demonstrates

This example shows the **complete modern Kubernetes workflow**:

1. **Infrastructure**: GKE cluster provisioned with CDKTF (Python)
2. **Containerization**: Docker for packaging applications
3. **Registry**: Google Container Registry for image storage
4. **Deployment**: Helm for application management
5. **Configuration**: Kubernetes-native config management
6. **Monitoring**: Standard kubectl commands for observability

This approach scales from development to production and follows industry best practices.