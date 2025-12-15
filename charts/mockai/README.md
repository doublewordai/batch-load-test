# MockAI Helm Chart

A simple Helm chart for deploying MockAI, an OpenAI Chat API mock server.

## Installation

```bash
helm install mockai ./charts/mockai
```

## Configuration

### Mock Responses

You can provide mock responses in two ways:

#### 1. Inline in values.yaml (default)

```yaml
mockResponses:
  content: |
    Response 1
    @@@@
    Response 2
    @@@@
    Response 3
```

#### 2. From a file

Place your responses file in `charts/mockai/files/` and reference it:

```yaml
mockResponses:
  file: "responses.txt"
```

Or use `--set-file` at install time:

```bash
helm install mockai ./charts/mockai \
  --set-file mockResponses.content=./my-responses.txt
```

### Environment Variables

Configure the mock server behavior via `values.yaml`:

```yaml
config:
  SERVER_PORT: "5002"
  MOCK_TYPE: "random"              # or "sequential"
  MOCK_FILE_SEPARATOR: "@@@@"      # Separator between responses
  RESPONSE_DELAY_MS: "500"         # Artificial delay
```

### Image Configuration

```yaml
image:
  repository: mockai
  tag: "latest"
  pullPolicy: IfNotPresent
```

### Service Configuration

```yaml
service:
  type: ClusterIP
  port: 5002
```

## Uninstallation

```bash
helm uninstall mockai
```
