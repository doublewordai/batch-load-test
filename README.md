# Batch Load Tests

Framework for sumulating batch user for the Doubleword Control Layer.

## Setup

### Database

We use Neon to host our postgres DB. To setup the DB create a branch of our production database called `load-test`. Then update the DATABASE_URL in ./control-layer.enc.yaml under the `secrets.controlLayer.data.DATABASE_URL`.

## Running

You can then deploy the load test infrastructure and tests to a k8s cluster using:

```bash
# Look at proposed changes
helmfile diff

# Sync state
helmfile apply
```
