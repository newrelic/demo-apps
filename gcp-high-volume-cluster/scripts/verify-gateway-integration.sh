#!/bin/bash
set -e

echo "========================================="
echo "Pipeline Control Gateway Integration Verification"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_passed() {
    echo -e "${GREEN}✓${NC} $1"
}

check_failed() {
    echo -e "${RED}✗${NC} $1"
}

check_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1. Verifying Gateway Deployment"
echo "================================"
GATEWAY_PODS=$(kubectl get pods -n newrelic -l app.kubernetes.io/name=pipeline-control-gateway --no-headers 2>/dev/null | wc -l)
if [ "$GATEWAY_PODS" -ge 1 ]; then
    READY_PODS=$(kubectl get pods -n newrelic -l app.kubernetes.io/name=pipeline-control-gateway --no-headers 2>/dev/null | grep -c "Running" || echo 0)
    check_passed "Gateway is running ($READY_PODS/$GATEWAY_PODS pods ready)"
    kubectl get pods -n newrelic -l app.kubernetes.io/name=pipeline-control-gateway
else
    check_failed "Gateway pods not found in newrelic namespace"
fi
echo ""

echo "2. Verifying Gateway Service Endpoints"
echo "======================================="
GATEWAY_SVC=$(kubectl get svc pipeline-control-gateway -n newrelic --no-headers 2>/dev/null | wc -l)
if [ "$GATEWAY_SVC" -eq 1 ]; then
    check_passed "Gateway service exists"
    kubectl get svc pipeline-control-gateway -n newrelic -o wide
    echo ""
    echo "Expected ports: 80 (New Relic protocol), 4317 (OTLP gRPC), 4318 (OTLP HTTP)"
else
    check_failed "Gateway service not found"
fi
echo ""

echo "3. Verifying Instrumentation CRD"
echo "================================="
INSTR=$(kubectl get instrumentation newrelic-instrumentation -n prod --no-headers 2>/dev/null | wc -l)
if [ "$INSTR" -eq 1 ]; then
    check_passed "Instrumentation CRD exists in prod namespace"
    kubectl get instrumentation newrelic-instrumentation -n prod -o yaml | grep -A 3 "OTEL_EXPORTER_OTLP_ENDPOINT" || check_warning "Could not verify OTLP endpoint configuration"
else
    check_failed "Instrumentation CRD not found in prod namespace"
    echo "   Run: kubectl apply -f k8s/instrumentation.yaml"
fi
echo ""

echo "4. Verifying nri-bundle Configuration"
echo "======================================"
INFRA_PODS=$(kubectl get pods -n newrelic -l app.kubernetes.io/name=newrelic-infrastructure --no-headers 2>/dev/null | wc -l)
if [ "$INFRA_PODS" -ge 1 ]; then
    check_passed "nri-bundle infrastructure pods running ($INFRA_PODS pods)"

    # Check if infrastructure is configured to use gateway
    SAMPLE_POD=$(kubectl get pods -n newrelic -l app.kubernetes.io/name=newrelic-infrastructure --no-headers 2>/dev/null | head -1 | awk '{print $1}')
    if [ -n "$SAMPLE_POD" ]; then
        echo "   Checking configuration for pod: $SAMPLE_POD"
        kubectl logs -n newrelic "$SAMPLE_POD" --tail=50 2>/dev/null | grep -i "collector_url\|gateway" | head -3 || check_warning "Could not verify gateway endpoint in logs"
    fi
else
    check_failed "nri-bundle infrastructure pods not found"
fi
echo ""

echo "5. Verifying App Auto-Instrumentation"
echo "======================================"
APP_PODS=$(kubectl get pods -n prod -l app --no-headers 2>/dev/null | wc -l)
if [ "$APP_PODS" -ge 1 ]; then
    check_passed "Application pods found ($APP_PODS pods)"

    # Check a sample app pod for agent injection
    SAMPLE_APP=$(kubectl get pods -n prod -l app=app-1 --no-headers 2>/dev/null | head -1 | awk '{print $1}')
    if [ -n "$SAMPLE_APP" ]; then
        echo "   Checking agent injection in pod: $SAMPLE_APP"
        INIT_CONTAINERS=$(kubectl get pod "$SAMPLE_APP" -n prod -o jsonpath='{.spec.initContainers[*].name}' 2>/dev/null)
        if echo "$INIT_CONTAINERS" | grep -q "newrelic-instrumentation"; then
            check_passed "New Relic agent init container found"
        else
            check_warning "Agent init container not found. Apps may need restart after Instrumentation CRD creation."
            echo "   Run: kubectl rollout restart deployment -n prod"
        fi

        # Check OTLP environment variables
        OTLP_ENDPOINT=$(kubectl exec -n prod "$SAMPLE_APP" -- env 2>/dev/null | grep OTEL_EXPORTER_OTLP_ENDPOINT || echo "")
        if [ -n "$OTLP_ENDPOINT" ]; then
            check_passed "OTLP environment variables configured"
            echo "   $OTLP_ENDPOINT"
        else
            check_warning "OTLP environment variables not found"
        fi
    fi
else
    check_warning "No application pods found in prod namespace"
fi
echo ""

echo "6. Gateway Metrics (Optional - requires port-forward)"
echo "======================================================"
echo "To check gateway metrics, run:"
echo "   kubectl port-forward -n newrelic svc/pipeline-control-gateway 8888:8888"
echo ""
echo "Then in another terminal:"
echo "   curl http://localhost:8888/metrics | grep -E 'receiver_accepted|processor_dropped|exporter_sent'"
echo ""
echo "Expected metrics:"
echo "   - otelcol_receiver_accepted_spans_total > 0"
echo "   - otelcol_receiver_accepted_metric_points_total > 0"
echo "   - otelcol_receiver_accepted_log_records_total > 0"
echo "   - otelcol_processor_dropped_spans_total > 0 (if drop rules working)"
echo ""

echo "7. Next Steps"
echo "============="
echo ""
echo "If verification passed:"
echo "  1. Check New Relic APM for 'GCP High Volume - App' services"
echo "  2. Verify distributed tracing data appears"
echo "  3. Confirm health check endpoints are NOT in traces (dropped by gateway)"
echo "  4. Monitor data volume in New Relic Account Settings → Usage"
echo ""
echo "If issues found:"
echo "  1. Update gateway filter rules: ./scripts/update-gateway-filter.sh"
echo "  2. Upgrade nri-bundle: helm upgrade nri-bundle newrelic/nri-bundle -n newrelic -f k8s/nri-bundle-values.yaml --set global.licenseKey=\$NEW_RELIC_LICENSE_KEY"
echo "  3. Restart apps: kubectl rollout restart deployment -n prod"
echo ""
echo "========================================="
echo "Verification Complete"
echo "========================================="
