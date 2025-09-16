# Simple Media Generator Helm Chart

This is a **minimal** Helm chart with only what you actually need.

## What's Included

- **`deployment.yaml`** - Runs your container (20 lines)
- **`service.yaml`** - Exposes your app (10 lines)
- **`values.yaml`** - Configuration (12 lines)

That's it! No bloat.

## Deploy

```bash
# Install
helm install media-generator ./media-generator-simple

# Upgrade
helm upgrade media-generator ./media-generator-simple

# Uninstall
helm uninstall media-generator
```

## Customize

Edit `values.yaml`:

```yaml
image:
  repository: gcr.io/your-project/your-app
  tag: v1.0.0

replicas: 5

service:
  type: LoadBalancer  # or NodePort, ClusterIP
```

## What We Removed from the Default Helm Template

❌ ServiceAccount (you probably don't need it)
❌ Ingress (use LoadBalancer for simplicity)
❌ HPA (add later if you need auto-scaling)
❌ Complex templating (keep it simple)
❌ Tests (add later if needed)
❌ 80+ lines of boilerplate per file

**Result**: 3 simple files instead of 8+ files with hundreds of lines of templating.

## When to Add Complexity

Add the other templates **only when you actually need them**:

- **Ingress** - When you need custom domain/SSL
- **HPA** - When you need auto-scaling
- **ServiceAccount** - When you need specific RBAC
- **ConfigMaps/Secrets** - When you have complex configuration

**Start simple, add complexity when needed!**
