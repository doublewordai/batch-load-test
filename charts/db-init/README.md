# Database Initialization Chart

A Kubernetes Job that initializes the control-layer database with models and group assignments.

## What it does

This chart runs a one-time Job (using Helm hooks) that:
1. Connects to the Neon PostgreSQL database using credentials from `control-layer-secret`
2. Inserts a model named "load-test" into the `models` table
3. Assigns the model to the "everyone" group (UUID: 00000000-0000-0000-0000-000000000000)

## Configuration

### Database Connection

The Job reads the `DATABASE_URL` from the Kubernetes secret:

```yaml
secret:
  name: control-layer-secret
  key: DATABASE_URL
```

### Models Configuration

Define models to insert in `values.yaml`:

```yaml
models:
  - name: "load-test"
    groupUuid: "00000000-0000-0000-0000-000000000000"
```

## Deployment

The chart is deployed via helmfile with a dependency on `control-layer`:

```yaml
- name: db-init
  namespace: {{ .Values.namespace }}
  chart: ./charts/db-init
  needs:
    - control-layer
```

This ensures the secret exists before the Job runs.

## Helm Hooks

The Job uses Helm hooks to run automatically:
- `post-install`: Runs after initial deployment
- `post-upgrade`: Runs after each upgrade
- `before-hook-creation`: Deletes previous Job before creating a new one

## SQL Operations

The Job performs these SQL operations:

```sql
-- Insert model (idempotent)
INSERT INTO models (name)
VALUES ('load-test')
ON CONFLICT (name) DO NOTHING;

-- Assign to group (idempotent)
INSERT INTO model_groups (model_id, group_id)
VALUES (model_id, '00000000-0000-0000-0000-000000000000')
ON CONFLICT (model_id, group_id) DO NOTHING;
```

All operations are idempotent - safe to run multiple times.

## Troubleshooting

Check Job status:
```bash
kubectl get jobs -n <namespace>
kubectl logs job/db-init-db-init -n <namespace>
```

If the Job fails:
- Verify the secret exists and contains valid DATABASE_URL
- Check database connectivity
- Review Job logs for SQL errors
