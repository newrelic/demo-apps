# Gateway TLS Configuration

This directory contains the Kubernetes manifests for configuring Java applications to connect to the New Relic Pipeline Control Gateway over HTTPS.

## Components

### 1. Gateway CA Certificate ConfigMap (`gateway-ca-cert.yaml`)

This ConfigMap contains the CA certificate that signed the gateway's TLS certificate. It must be created in both:
- `newrelic` namespace (for gateway pods)
- `prod` namespace (for application pods)

**To populate with your CA certificate:**

```bash
# Extract your gateway CA certificate
kubectl get secret -n newrelic gateway-tls-cert -o jsonpath='{.data.ca\.crt}' | base64 -d > /tmp/gateway-ca.crt

# Create the ConfigMap in both namespaces
kubectl create configmap gateway-ca-cert --from-file=ca.crt=/tmp/gateway-ca.crt -n newrelic --dry-run=client -o yaml > k8s/gateway-ca-cert.yaml
kubectl create configmap gateway-ca-cert --from-file=ca.crt=/tmp/gateway-ca.crt -n prod --dry-run=client -o yaml >> k8s/gateway-ca-cert.yaml
```

### 2. Application Template (`app-template.yaml`)

The application template includes:

**Init Container (`import-gateway-ca`):**
- Uses `eclipse-temurin:17-jre` image
- Copies Java's default cacerts truststore
- Imports the gateway CA certificate into the truststore
- Makes the truststore available to the application container

**Environment Variables:**
- `JAVA_TOOL_OPTIONS`: Configures the Java agent and truststore location

**Volumes:**
- `truststore`: EmptyDir volume containing the Java truststore with imported CA
- `gateway-ca`: ConfigMap volume mounting the CA certificate

### 3. Instrumentation CRD (`instrumentation.yaml`)

Configures the New Relic Java agent auto-injection:
- Agent image: `newrelic/newrelic-java-init:latest`
- Gateway endpoint: `pipeline-control-gateway.newrelic.svc.cluster.local:443`
- CA bundle path: `/etc/ssl/certs/gateway-ca.crt`
- Namespace selector: Only instruments pods in `prod` namespace

## How It Works

1. **Agent Injection**: The `k8s-agents-operator` automatically injects the New Relic Java agent into pods with the annotation `instrumentation.newrelic.com/inject-java: "true"`

2. **Truststore Preparation**: The `import-gateway-ca` init container runs before the application starts:
   - Copies the default Java cacerts truststore
   - Imports the gateway's CA certificate
   - Stores it in `/truststore/cacerts`

3. **Agent Configuration**: The Java agent is configured via environment variables:
   - `NEW_RELIC_HOST`: Gateway hostname
   - `NEW_RELIC_PORT`: 443 (HTTPS)
   - `NEW_RELIC_CA_BUNDLE_PATH`: Path to CA certificate
   - `JAVA_TOOL_OPTIONS`: Truststore location for TLS validation

4. **Data Flow**:
   ```
   Java App → New Relic Agent (with custom truststore)
       ↓ HTTPS/TLS (port 443)
   Pipeline Control Gateway (validates client, presents server cert)
       ↓ Process & Filter
   New Relic Platform
   ```

## Deployment Steps

1. **Deploy namespace and gateway CA ConfigMap:**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/gateway-ca-cert.yaml
   ```

2. **Deploy New Relic infrastructure (includes operator):**
   ```bash
   helm install nr-infra newrelic/nri-bundle \
     --namespace newrelic \
     -f k8s/nri-bundle-values.yaml
   ```

3. **Deploy instrumentation CRD:**
   ```bash
   kubectl apply -f k8s/instrumentation.yaml
   ```

4. **Deploy applications:**
   ```bash
   # Using the template (replace {{NUM}} and {{PROJECT_ID}})
   for i in {1..12}; do
     sed -e "s/{{NUM}}/$i/g" \
         -e "s/{{PROJECT_ID}}/your-project-id/g" \
         k8s/app-template.yaml | kubectl apply -f -
   done
   ```

## Verification

**Check agent injection:**
```bash
kubectl get pods -n prod -l app=app-1 -o jsonpath='{.items[0].spec.initContainers[*].name}'
# Should output: import-gateway-ca nri-java--app
```

**Check agent connection:**
```bash
APP_POD=$(kubectl get pods -n prod -l app=app-1 -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n prod $APP_POD -- cat /nri-java--app/logs/newrelic_agent.log | grep "connected"
```

**Check gateway data flow:**
```bash
GATEWAY_POD=$(kubectl get pods -n newrelic -l app.kubernetes.io/name=pipeline-control-gateway -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n newrelic $GATEWAY_POD -- sh -c 'curl -s http://localhost:8888/metrics | grep "otelcol_receiver_accepted"'
```

## Troubleshooting

**"unable to find valid certification path" error:**
- Verify the CA certificate matches the gateway's TLS certificate issuer
- Check that the gateway-ca-cert ConfigMap exists in the prod namespace
- Verify the init container completed successfully

**"TLS handshake error" in gateway logs:**
- These errors are typically from logging/infrastructure agents (not apps)
- Check app logs specifically to confirm app connections are successful

**No data in New Relic:**
- Verify gateway metrics show data being received and sent
- Check gateway logs for export errors
- Confirm license key is correct
