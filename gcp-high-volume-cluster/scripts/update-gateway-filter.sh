#!/bin/bash
set -e

echo "Updating Pipeline Control Gateway drop rules..."
echo ""
echo "This will replace the overly aggressive traces filter that drops ALL successful requests"
echo "with a more targeted filter that only drops health check endpoints."
echo ""

# Create a temporary file with the updated filter configuration
cat > /tmp/gateway-filter-patch.yaml << 'EOF'
processors:
  # Drop health check endpoints (UPDATED - was too aggressive before)
  filter/Traces:
    error_mode: ignore
    traces:
      span:
        # Drop health/readiness check endpoints
        - 'attributes["http.target"] == "/health"'
        - 'attributes["http.target"] == "/ready"'
        - 'attributes["http.target"] == "/alive"'

        # FUTURE: Add more drop rules here as needed
        # Examples (commented out for future use):
        # - 'attributes["http.status_code"] == 200 and duration < 10000000'  # Fast successful requests
        # - 'resource.attributes["service.name"] =~ "app-(9|10|11|12)"'      # Specific services
        # - 'name == "GET /static/*"'                                          # Static assets

  # Drop debug logs from background workers
  filter/Logs:
    logs:
      log_record:
        - severity_text == "DEBUG" and resource.attributes["service.name"] == "background-worker"

  # Drop internal and test metrics
  filter/Metrics:
    metrics:
      metric:
        - IsMatch(name, "^internal\\.")
        - IsMatch(name, "^test_")
EOF

echo "Current gateway filter configuration:"
echo "======================================"
kubectl get configmap pipeline-control-gateway-config -n newrelic -o jsonpath='{.data.deployment-config\.yaml}' | grep -A 10 "filter/Traces" || echo "Could not retrieve current config"
echo ""
echo ""

echo "NOTE: This script shows the updated filter configuration."
echo "To apply it, you need to:"
echo ""
echo "1. Manually edit the ConfigMap:"
echo "   kubectl edit configmap pipeline-control-gateway-config -n newrelic"
echo ""
echo "2. Replace the 'processors.filter/Traces' section with:"
cat /tmp/gateway-filter-patch.yaml
echo ""
echo "3. Save and exit the editor"
echo ""
echo "4. Restart gateway pods to pick up the new config:"
echo "   kubectl rollout restart deployment pipeline-control-gateway -n newrelic"
echo ""
echo "Updated filter configuration has been saved to: /tmp/gateway-filter-patch.yaml"
echo ""
echo "For production, consider managing gateway config via Helm values if the chart supports it."
