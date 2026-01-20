# Hybrid Agent Observability Demo

A comprehensive Node.js microservices e-commerce demo showcasing three observability approaches: **Native APM**, **OpenTelemetry**, and **Hybrid** instrumentation with New Relic.

## Overview

This demo provides a side-by-side comparison of three instrumentation strategies for the same application architecture:

1. **APM Variant** - New Relic native agent with proprietary APIs
2. **OTel Variant** - Pure OpenTelemetry SDK with OTLP export to New Relic
3. **Hybrid Variant** - New Relic agent with OpenTelemetry bridge (uses OTel APIs)

All three variants run simultaneously, allowing you to compare distributed tracing, logs in context, and observability capabilities across different instrumentation approaches.

## Architecture

### Services

- **Storefront** (React + Vite) - E-commerce frontend with New Relic Browser monitoring
- **Order Service** - Checkout orchestration (ports 3000/3001/3002 for APM/OTel/Hybrid)
- **Inventory Service** - Stock management with PostgreSQL (ports 4000/4001/4002)
- **Payment Service** - Payment processing with simulated delays (ports 5000/5001/5002)
- **PostgreSQL** - Shared database for all variants (port 5432)
- **Load Generator** - Selenium-based automated traffic generation

### Service Map

```
┌─────────────────────────────────────────────────────────────────┐
│                       Load Generator                            │
│                    (Selenium WebDriver)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Storefront (Port 8080)                   │
│                    React + Vite + Nginx                         │
│              [New Relic Browser Agent - Optional]               │
└───────────────┬─────────────────┬────────────────┬──────────────┘
                │                 │                │
    Variant     │    Variant      │    Variant     │
    Selector    │    Selector     │    Selector    │
                │                 │                │
       ┌────────▼────────┐  ┌─────▼──────┐  ┌──────▼──────┐
       │  Order Service  │  │   Order    │  │   Order     │
       │      (APM)      │  │  Service   │  │  Service    │
       │   Port 3000     │  │  (OTel)    │  │  (Hybrid)   │
       └────────┬────────┘  │Port 3001   │  │ Port 3002   │
                │           └─────┬──────┘  └──────┬──────┘
                │                 │                │
                └─────────────────┴────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  │               │               │
       HTTP POST /checkout   HTTP GET/POST   HTTP POST
                  │               │               │
        ┌─────────▼─────────┐     │    ┌──────────▼──────────┐
        │ Inventory Service │     │    │                     │
        │                   │◄────┘    │  Payment Service    │
        │  (APM/OTel/Hybrid)│          │ (APM/OTel/Hybrid)   │
        │ Ports 4000-4002   │          │  Ports 5000-5002    │
        └────────┬──────────┘          └─────────────────────┘
                 │                            │
    SQL Queries  │                            │ Simulated
    (pg driver)  │                            │ 2s Delay
                 ▼
        ┌─────────────────┐
        │   PostgreSQL    │
        │    Port 5432    │
        │                 │
        │  Tables:        │
        │  - products     │
        │  - orders       │
        └─────────────────┘

Instrumentation Flow (All Services):
- APM Variant:    New Relic Agent (native instrumentation) → collector.newrelic.com
- OTel Variant:   OTel SDK → OTLP → https://otlp.nr-data.net
- Hybrid Variant: New Relic Agent (with OTel bridge) → collector.newrelic.com
                  └─ Uses OpenTelemetry instrumentation internally
                  └─ Custom instrumentation via @opentelemetry/api
```

### Request Flow Details

**1. User Checkout (via Browser or Load Generator)**
```
Storefront → POST /checkout → Order Service
```

**2. Order Service Orchestration**
```
Order Service → GET /inventory/:sku → Inventory Service
              → POST /reserve → Inventory Service
              → POST /process-payment → Payment Service
              → INSERT INTO orders → (via Inventory Service)
```

**3. Inventory Service Database Operations**
```
Inventory Service → SELECT FROM products → PostgreSQL
                  → UPDATE products SET reserved → PostgreSQL
```

**4. Distributed Trace Propagation**
- W3C Trace Context headers automatically propagated across all HTTP calls
- APM variant also sends New Relic distributed tracing headers
- Hybrid variant sends both W3C headers (from OTel) and NR headers (from APM)

### Demo Features

- **Distributed Tracing** - Full trace propagation across all services
- **Logs in Context** - Automatic trace ID injection into logs
- **Bottleneck Detection** - 2-second payment delay demonstrates performance issues
- **Error Tracking** - Out-of-stock scenarios generate tracked errors
- **Browser Monitoring** (Optional) - Frontend performance correlation with backend traces
- **Load Generation** - Automated scenarios for continuous traffic

## Prerequisites

- Docker and Docker Compose
- New Relic account (free tier works)
- 8GB+ RAM recommended for running all containers

## Quick Start

### 1. Clone and Setup

```bash
cd hybrid-agent
cp .env.sample .env
```

### 2. Configure New Relic Credentials

Edit `.env` and add your New Relic credentials:

```bash
# Required
NEW_RELIC_LICENSE_KEY=your_license_key_here
NEW_RELIC_ACCOUNT_ID=your_account_id

# Optional - for Browser monitoring
NEW_RELIC_TRUST_KEY=your_trust_key
NEW_RELIC_BROWSER_AGENT_ID=your_browser_agent_id
NEW_RELIC_BROWSER_APP_ID=your_browser_app_id
```

**Where to find these:**
- License Key: New Relic UI → Account Settings → API Keys
- Account ID: Visible in New Relic URL (e.g., `https://one.newrelic.com/nr1-core?account=YOUR_ACCOUNT_ID`)
- Region: `US` or `EU` depending on your New Relic account location
- Browser Agent credentials: New Relic UI → Browser → Settings (optional - see note below)

**Note on Browser Monitoring:**
Browser monitoring is **optional**. If you don't configure the `NEW_RELIC_BROWSER_*` variables (or leave them as the default placeholder values), the demo will run perfectly fine with just APM/OTel/Hybrid backend instrumentation. Browser monitoring adds frontend correlation but is not required to see distributed traces.

### 3. Start the Demo

```bash
# Build and start all services (this will take a few minutes on first run)
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d
```

**Running without Browser Monitoring:**
If you skip configuring the Browser agent variables (leave them as defaults), the demo will:
- ✅ Still generate distributed traces across all backend services
- ✅ Show logs in context with trace correlation
- ✅ Demonstrate APM/OTel/Hybrid instrumentation differences
- ✅ Run the Selenium load generator successfully
- ❌ Not capture frontend metrics (page load, AJAX timing, etc.)

This is perfectly fine for demonstrating backend observability!

### 4. Access the Application

- **Storefront**: http://localhost:8080
- **APM Order Service**: http://localhost:3000/health
- **OTel Order Service**: http://localhost:3001/health
- **Hybrid Order Service**: http://localhost:3002/health

### 5. View Traces in New Relic

1. Go to **APM & Services** in New Relic
2. You should see 9 services (3 per variant):
   - NRDEMO Order Service (APM/OTel/Hybrid)
   - NRDEMO Inventory Service (APM/OTel/Hybrid)
   - NRDEMO Payment Service (APM/OTel/Hybrid)
3. Click any service → **Distributed tracing** to see traces
4. View **Logs in context** for correlated log entries
5. Check **Service map** to visualize dependencies

## Using the Demo

### Manual Testing

1. Open http://localhost:8080 in your browser
2. Select a backend variant from the dropdown (APM, OTel, or Hybrid)
3. Add products to cart
4. Click "Proceed to Checkout"
5. Fill in customer ID (e.g., `CUST-001`)
6. Click "Complete Order"
7. Wait ~2 seconds for payment processing
8. View the distributed trace in New Relic

### Automated Load Generation

The load generator automatically runs three scenarios every 30 seconds:

1. **Happy Path** - Successful purchase
2. **Out of Stock** - Attempts to buy unavailable items
3. **Slow Payment** - Large order demonstrating payment bottleneck

Load generation starts automatically with `docker-compose up`.

## Demo Scenarios

### 1. Bottleneck Detection

**Scenario:** The payment service has an intentional 2-second delay

**How to Demo:**
1. Complete a checkout in the UI
2. Go to New Relic → Distributed Tracing
3. Find the trace for your order
4. Notice the payment service span taking ~2 seconds
5. This demonstrates how distributed tracing identifies performance bottlenecks

### 2. Comparing Instrumentation Types

**How to Demo:**
1. Complete one order using APM variant (port 3000)
2. Complete another using OTel variant (port 3001)
3. Complete a third using Hybrid variant (port 3002)
4. Compare the traces in New Relic
5. Notice similarities and differences in:
   - Span naming conventions
   - Custom attributes
   - Instrumentation detail level

### 3. Logs in Context

**How to Demo:**
1. Complete a checkout
2. In New Relic, find the distributed trace
3. Click on any span → "Logs"
4. See correlated log entries with trace IDs
5. Click a log entry to see full context

### 4. Error Tracking

**Scenario:** Out-of-stock items generate errors

**How to Demo:**
1. The Gaming Headset (HEADSET-001) is out of stock
2. Errors appear in New Relic Errors Inbox
3. View error details with full stack traces
4. See correlated logs and traces

## Project Structure

```
hybrid-agent/
├── docker-compose.yml          # Orchestration for all 13 containers
├── .env.sample                 # Configuration template
├── .gitignore
├── README.md
├── scripts/
│   └── init-db.sql            # PostgreSQL schema + seed data
├── storefront/
│   ├── public/
│   │   └── index.html         # NR Browser agent injection point
│   ├── src/
│   │   ├── App.jsx            # Main app with variant selector
│   │   ├── components/        # Product catalog, cart, checkout
│   │   └── services/
│   │       └── api.js         # Backend API client
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── services/
│   ├── shared/
│   │   ├── logger.js          # Pino with trace context
│   │   └── db.js              # PostgreSQL connection pool
│   ├── order-service/
│   │   ├── index.js           # Entry point - loads telemetry based on VARIANT
│   │   ├── routes/
│   │   │   └── checkout.js    # Business logic with custom attributes
│   │   ├── telemetry/
│   │   │   ├── apm.js         # Loads New Relic agent (OTel bridge OFF)
│   │   │   ├── otel.js        # Initializes OpenTelemetry SDK
│   │   │   └── hybrid.js      # Loads New Relic agent (OTel bridge ON)
│   │   ├── newrelic.js        # New Relic config (shared by APM & Hybrid)
│   │   ├── Dockerfile.apm
│   │   ├── Dockerfile.otel
│   │   ├── Dockerfile.hybrid
│   │   └── package.json
│   ├── inventory-service/
│   │   └── [same structure as order-service]
│   └── payment-service/
│       └── [same structure as order-service]
└── load-generator/
    ├── index.js               # Orchestrator
    ├── scenarios/
    │   ├── happy-path.js
    │   ├── out-of-stock.js
    │   └── slow-payment.js
    ├── Dockerfile
    └── package.json
```

## Instrumentation Details

### How Initialization Works

Each service supports three instrumentation variants, determined by the `VARIANT` environment variable set in docker-compose.yml:

```javascript
// index.js - Service entry point
const variant = process.env.VARIANT || 'apm';

if (variant === 'apm') {
  telemetry = require('./telemetry/apm');
} else if (variant === 'otel') {
  telemetry = require('./telemetry/otel');
} else if (variant === 'hybrid') {
  telemetry = require('./telemetry/hybrid');
}

// IMPORTANT: Telemetry must be loaded BEFORE any instrumented libraries
const express = require('express');
```

**Key Points:**
- **APM and Hybrid both use the same `newrelic.js` config file**
  - APM: `newrelic.js` has `opentelemetry.enabled: false` (because `VARIANT !== 'hybrid'`)
  - Hybrid: `newrelic.js` has `opentelemetry.enabled: true` (because `VARIANT === 'hybrid'`)
- **OTel is completely independent** - doesn't load or use `newrelic.js` at all
- Each Docker container runs only one variant, so there's no conflict

### APM Variant (Native New Relic)

**How it works:**

```javascript
// telemetry/apm.js
const newrelic = require('newrelic');
// Loads newrelic.js config with opentelemetry.enabled: false

// Automatic instrumentation for:
// - HTTP/HTTPS requests
// - Express middleware
// - PostgreSQL queries
// - Distributed tracing (W3C + NR headers)
```

**Custom Instrumentation:**
```javascript
// Uses New Relic's native API
const newrelic = require('newrelic');
newrelic.addCustomSpanAttributes({
  'order.id': orderId,
  'customer.id': customerId
});
```

**Data Flow:**
```
Application Code
    ↓
New Relic Agent (native instrumentation)
    ├─ Automatic instrumentation (HTTP, Express, pg)
    ├─ Custom spans via New Relic API
    ↓
collector.newrelic.com
```

**Pros:**
- Zero-config automatic instrumentation
- Rich APM features (slow SQL, external services, error tracking)
- Native New Relic integration with full platform features
- Logs in context with getLinkingMetadata()
- Battle-tested, production-ready

**Cons:**
- Vendor-specific (New Relic only)
- Uses proprietary APIs (not portable to other backends)

### OTel Variant (OpenTelemetry SDK)

**How it works:**

The OTel variant uses the full OpenTelemetry SDK, completely independent of the New Relic agent:

```javascript
// telemetry/otel.js
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');

// Region-aware OTLP endpoint configuration
const region = (process.env.NEW_RELIC_REGION || 'US').toUpperCase();
const otlpEndpoints = {
  US: {
    traces: 'https://otlp.nr-data.net/v1/traces',
    metrics: 'https://otlp.nr-data.net/v1/metrics'
  },
  EU: {
    traces: 'https://otlp.eu01.nr-data.net/v1/traces',
    metrics: 'https://otlp.eu01.nr-data.net/v1/metrics'
  }
};

// Initialize OpenTelemetry SDK
const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: process.env.NEW_RELIC_APP_NAME
  }),
  spanProcessor: new BatchSpanProcessor(traceExporter),
  metricReader: new PeriodicExportingMetricReader({ exporter: metricExporter }),
  instrumentations: [getNodeAutoInstrumentations({
    '@opentelemetry/instrumentation-http': { enabled: true },
    '@opentelemetry/instrumentation-express': { enabled: true },
    '@opentelemetry/instrumentation-pg': { enabled: true }
  })]
});

sdk.start();
```

**Custom Instrumentation:**
```javascript
// Uses OpenTelemetry API
const { trace } = require('@opentelemetry/api');
const span = trace.getActiveSpan();
if (span) {
  span.setAttributes({
    'order.id': orderId,
    'customer.id': customerId
  });
}
```

**Data Flow:**
```
Application Code
    ↓
OpenTelemetry Auto-Instrumentations (HTTP, Express, pg)
    ↓
OpenTelemetry SDK
    ├─ BatchSpanProcessor
    ├─ PeriodicExportingMetricReader
    ↓
OTLP Exporters
    ↓
otlp.nr-data.net (or otlp.eu01.nr-data.net for EU)
```

**Pros:**
- **Vendor-neutral** - Can send to any OTLP-compatible backend (not just New Relic)
- **Standardized** - Uses W3C and OpenTelemetry specifications
- **Full control** - Fine-grained configuration over all instrumentation
- **Portable** - Switch backends by changing exporter configuration
- **Growing ecosystem** - Access to all OpenTelemetry instrumentation libraries

**Cons:**
- More configuration required (~140 lines vs ~20 for Hybrid)
- Requires explicit SDK lifecycle management (start/shutdown)
- Some New Relic platform features may not be available via OTLP

### Hybrid Variant: New Relic with OpenTelemetry Bridge

The hybrid variant demonstrates the **recommended** approach for using OpenTelemetry APIs with New Relic. It provides the simplicity of New Relic APM with the flexibility of OpenTelemetry APIs.

**How it works:**

The hybrid approach uses a single configuration file (`newrelic.js`) that is shared between APM and Hybrid variants, with conditional logic to enable the OpenTelemetry bridge only for the Hybrid variant:

1. **Shared Configuration** (`newrelic.js`):
```javascript
exports.config = {
  // Enable OpenTelemetry bridge ONLY for hybrid variant
  opentelemetry: {
    enabled: process.env.VARIANT === 'hybrid',
    traces: { enabled: process.env.VARIANT === 'hybrid' },
    metrics: { enabled: process.env.VARIANT === 'hybrid' }
  },
  distributed_tracing: { enabled: true },
  application_logging: {
    enabled: true,
    forwarding: { enabled: true }
  }
  // ... other standard New Relic configuration
};
```

**Why this works:** Both APM and Hybrid variants call `require('newrelic')`, which loads this configuration file. The `VARIANT` environment variable determines whether the OpenTelemetry bridge is enabled.

2. **Initialization Flow**:
```javascript
// index.js - Entry point
const variant = process.env.VARIANT || 'apm';

if (variant === 'apm') {
  telemetry = require('./telemetry/apm');    // loads New Relic with OTel bridge OFF
} else if (variant === 'hybrid') {
  telemetry = require('./telemetry/hybrid'); // loads New Relic with OTel bridge ON
}

// telemetry/apm.js and telemetry/hybrid.js both do the same thing:
const newrelic = require('newrelic');  // Reads newrelic.js config
module.exports = newrelic;
```

**Key Point:** The telemetry files don't configure anything - they just load the New Relic agent. The agent reads `newrelic.js` and sees whether to enable the OTel bridge based on the `VARIANT` environment variable.

3. **Automatic Instrumentation**:

When `opentelemetry.enabled: true`, the New Relic agent automatically:
- Uses OpenTelemetry-compatible instrumentation internally
- Instruments HTTP, Express, PostgreSQL, and other frameworks
- Propagates W3C Trace Context headers
- Bridges all data to New Relic's collector

**No manual instrumentation registration needed!** The agent handles it automatically.

4. **Custom Instrumentation**:

The key difference between variants is in custom instrumentation:

**APM Variant:**
```javascript
// Uses New Relic's span attribute API
const newrelic = require('newrelic');
newrelic.addCustomSpanAttributes({
  'order.id': orderId,
  'customer.id': customerId
});
```

**Hybrid Variant:**
```javascript
// Uses OpenTelemetry API
const { trace } = require('@opentelemetry/api');
const span = trace.getActiveSpan();
if (span) {
  span.setAttributes({
    'order.id': orderId,
    'customer.id': customerId
  });
}
```

**Data Flow:**
```
Application Code
    ↓
New Relic Agent (with opentelemetry.enabled: true)
    ├─ Automatic OTel-compatible instrumentation (HTTP, Express, pg)
    ├─ Accepts custom instrumentation via @opentelemetry/api
    ├─ Bridges all OTel data internally
    ↓
collector.newrelic.com (all telemetry data)
```

**Important:** All data goes to `collector.newrelic.com`, not `otlp.nr-data.net`. The New Relic agent handles the bridging internally.

**Pros:**
- **Extremely simple** - Just enable a flag in configuration
- **Single agent** - No separate OTel SDK needed
- **Automatic instrumentation** - No manual registration required
- **OTel API compatible** - Use standard `@opentelemetry/api` for custom spans
- **Single data destination** - Everything goes to collector.newrelic.com
- **Production-ready** - New Relic's recommended approach

**Cons:**
- Requires New Relic agent version 11.0.0+ for full OTel bridge support
- Tied to New Relic's data pipeline (can't send to other backends)

**When to use:**
- You want to use OpenTelemetry APIs but send data to New Relic
- You're migrating from New Relic APM to OpenTelemetry gradually
- You want the simplicity of APM with the flexibility of OTel APIs
- You need both New Relic's platform features AND OTel API compatibility

**When NOT to use:**
- You need to send data to multiple observability backends
- You need advanced OTel SDK features not supported by the bridge
- You want vendor neutrality (use pure OTel variant instead)

**Reference:** https://github.com/newrelic/newrelic-node-examples/tree/main/opentelemetry-example

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `NEW_RELIC_LICENSE_KEY` | Your NR license key | - | **Yes** |
| `NEW_RELIC_ACCOUNT_ID` | Your NR account ID | - | **Yes** |
| `NEW_RELIC_REGION` | New Relic region (`US` or `EU`) | `US` | No |
| `NEW_RELIC_BROWSER_AGENT_ID` | Browser agent ID | placeholder | **No** |
| `NEW_RELIC_BROWSER_APP_ID` | Browser app ID | placeholder | **No** |
| `NEW_RELIC_TRUST_KEY` | Browser trust key | placeholder | **No** |
| `PAYMENT_DELAY_MS` | Payment processing delay | 2000 | No |
| `PAYMENT_ERROR_RATE` | Random error rate (0-1) | 0.1 | No |
| `SCENARIO_INTERVAL_MS` | Time between load gen scenarios | 30000 | No |
| `SCENARIOS` | Enabled scenarios | all | No |

**New Relic Region:**
The `NEW_RELIC_REGION` variable controls where OpenTelemetry traces are sent:
- `US` (default): Sends to `https://otlp.nr-data.net/v1/traces`
- `EU`: Sends to `https://otlp.eu01.nr-data.net/v1/traces`

Set this based on where your New Relic account is located. This **only affects OTel variant services** - APM and Hybrid variants automatically detect the correct region.

**Browser Agent Variables:**
If you leave the Browser agent variables with their default placeholder values, the Browser agent will not be initialized. The storefront will detect this and skip Browser monitoring entirely. The demo will work perfectly with just APM/OTel/Hybrid backend instrumentation.

### Service Naming Convention

Services follow this pattern:
```
NRDEMO <ServiceName> (<Variant>)
```

Examples:
- `NRDEMO Order Service (APM)`
- `NRDEMO Inventory Service (OTel)`
- `NRDEMO Payment Service (Hybrid)`

## Troubleshooting

### Services not starting

```bash
# Check service status
docker-compose ps

# View logs for a specific service
docker-compose logs order-service-apm

# Restart all services
docker-compose restart
```

### No traces in New Relic

1. Verify `NEW_RELIC_LICENSE_KEY` is set correctly in `.env`
2. Check service logs for connection errors
3. Ensure your firewall allows outbound HTTPS (443) to New Relic
4. Wait 1-2 minutes for data to appear in the UI

### Database connection errors

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Load generator not working

```bash
# Check load generator logs
docker-compose logs load-generator

# Ensure storefront is accessible
curl http://localhost:8080

# Restart load generator
docker-compose restart load-generator
```

## Cleaning Up

```bash
# One-liner
docker-compose down -v --rmi all

# Or step by step
# Stop all services
docker-compose down

# Remove volumes (deletes database data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Performance Notes

- **First Run**: Building all containers takes 5-10 minutes
- **Subsequent Runs**: Starting services takes 30-60 seconds
- **Resource Usage**: ~4-6GB RAM for all containers
- **Storage**: ~2-3GB for Docker images

## Contributing

This demo is for educational purposes. Feel free to:
- Add new scenarios
- Implement additional services
- Enhance instrumentation examples
- Improve documentation

## License

This is demo code and is not intended for production use.

## Additional Resources

- [New Relic APM Documentation](https://docs.newrelic.com/docs/apm/)
- [OpenTelemetry Node.js](https://opentelemetry.io/docs/instrumentation/js/)
- [New Relic OpenTelemetry](https://docs.newrelic.com/docs/more-integrations/open-source-telemetry-integrations/opentelemetry/opentelemetry-introduction/)
- [Distributed Tracing](https://docs.newrelic.com/docs/distributed-tracing/concepts/introduction-distributed-tracing/)
