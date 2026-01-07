# AI Monitoring Demo - Flask UI

Flask-based web application for demonstrating New Relic AI monitoring capabilities with autonomous system repair, model comparison, and hallucination detection.

## Features

### 🔧 Repair System
- Autonomous system repair with Docker container monitoring
- Side-by-side model comparison (llama3.2:1b vs qwen2.5:0.5b)
- Real-time container status updates via polling
- Container logs viewer

### 💬 Chat Assistant
- Interactive chat interface with persistent session history
- Model comparison mode
- Example prompts for boundary testing
- Hallucination detection demonstration

### 📊 Model Comparison Dashboard
- Performance metrics and analytics
- Interactive Plotly.js charts (latency, success rate)
- Automated insights generation
- Metrics export (JSON)

## Architecture

- **Frontend:** Flask + Jinja2 templates with vanilla JavaScript
- **Real-time Updates:** AJAX polling (15s for containers, 30s for health, 10s for metrics)
- **Charts:** Plotly.js for interactive visualizations
- **State Management:** Flask sessions (filesystem storage, upgradable to Redis)
- **Monitoring:** New Relic browser + backend monitoring (automatic via APM agent)
- **Deployment:** Docker + gunicorn (4 workers)

## Project Structure

```
flask-ui/
├── app.py                      # Flask application factory
├── wsgi.py                     # WSGI entry point
├── config.py                   # Configuration
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── newrelic.ini               # New Relic configuration
│
├── routes/                     # Flask blueprints
│   ├── main.py                # Home page
│   ├── repair.py              # Repair mode
│   ├── chat.py                # Chat mode
│   ├── comparison.py          # Comparison dashboard
│   └── api.py                 # AJAX API endpoints
│
├── services/                   # Business logic
│   ├── agent_client.py        # AI Agent API client
│   └── mcp_client.py          # MCP Server API client
│
├── templates/                  # Jinja2 templates
│   ├── base.html              # Base layout
│   ├── components/            # Reusable components
│   └── pages/                 # Page templates
│
├── static/                     # Static assets
│   ├── css/                   # Stylesheets
│   ├── js/                    # JavaScript
│   └── vendor/                # Third-party libraries (Plotly.js)
│
└── utils/                      # Utilities
    └── session_helpers.py     # Flask session management
```

## Routes

### Page Routes
- `GET /` - Home page (redirects to repair mode)
- `GET /repair` - Repair system page
- `GET /chat` - Chat interface page
- `GET /comparison` - Model comparison dashboard

### API Endpoints (Polled by JavaScript)
- `GET /api/health` - Agent health status (30s poll)
- `GET /api/metrics` - Model metrics (10s poll)
- `GET /api/containers` - Docker container status (15s poll)
- `GET /api/logs/<container>` - Container logs
- `GET /api/load-test/status` - Load test statistics (5s poll)
- `POST /api/load-test/start` - Start load test
- `POST /api/load-test/stop` - Stop load test

### Action Routes
- `POST /repair/trigger` - Trigger repair workflow
- `POST /repair/compare` - Compare both models
- `POST /chat/send` - Send chat message
- `POST /chat/compare` - Compare chat responses
- `POST /chat/clear` - Clear chat history
- `GET /comparison/export` - Export metrics JSON

## Environment Variables

- `AGENT_URL` - AI Agent service URL (default: http://ai-agent:8001)
- `MCP_URL` - MCP Server URL (default: http://mcp-server:8002)
- `SECRET_KEY` - Flask secret key (auto-generated if not set, **change in production!**)
- `NEW_RELIC_LICENSE_KEY` - New Relic license key
- `NEW_RELIC_APP_NAME` - Application name for New Relic (e.g., aim-demo_flask-ui)
- `NEW_RELIC_CONFIG_FILE` - Path to newrelic.ini (default: /app/newrelic.ini)

### Setting Environment Variables

Add these to your `.env` file in the project root:

```bash
# Flask UI Configuration
AGENT_URL=http://ai-agent:8001
MCP_URL=http://mcp-server:8002
FLASK_SECRET_KEY=your-secret-key-here-change-in-production

# New Relic
NEW_RELIC_LICENSE_KEY=your_license_key
NEW_RELIC_APP_NAME_FLASK_UI=aim-demo_flask-ui
```

## Running Locally (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AGENT_URL=http://localhost:8001
export MCP_URL=http://localhost:8002

# Run Flask development server
python app.py
```

Access at: http://localhost:8501

## Running with Docker

```bash
# Build image
docker build -t flask-ui .

# Run container
docker run -p 8501:8501 \
  -e AGENT_URL=http://ai-agent:8001 \
  -e MCP_URL=http://mcp-server:8002 \
  -e NEW_RELIC_LICENSE_KEY=your_license_key \
  flask-ui
```

## Deployment Guide

### Quick Start

#### 1. Environment Setup

Edit `.env` file in the project root (one directory up):

```bash
# Flask UI Configuration
AGENT_URL=http://ai-agent:8001
MCP_URL=http://mcp-server:8002
FLASK_SECRET_KEY=your-secret-key-here-change-in-production

# New Relic
NEW_RELIC_LICENSE_KEY=your_license_key
NEW_RELIC_APP_NAME_FLASK_UI=aim-demo_flask-ui
```

**Generate a secure secret key:**
```bash
python3 -c "import os; print(os.urandom(32).hex())"
```

#### 2. Build and Deploy

```bash
# From the ai-monitoring directory (project root)
cd ..

# Build Flask UI image
docker-compose build flask-ui

# Start all services
docker-compose up -d

# Or start Flask UI only (if other services are running)
docker-compose up -d flask-ui
```

#### 3. Verify Deployment

```bash
# Check Flask UI logs
docker-compose logs -f flask-ui

# Check all running services (should show 8)
docker-compose ps

# Access the application
open http://localhost:8501
```

**Expected log output:**
```
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:8501 (1)
[INFO] Using worker: sync
[INFO] Booting worker with pid: 7
[INFO] Booting worker with pid: 8
[INFO] Booting worker with pid: 9
[INFO] Booting worker with pid: 10
```

### Deployment Verification

#### Service Health Check

```bash
# All 8 services should be running
docker-compose ps

# Expected output:
# aim-ollama-model-a    running (healthy)
# aim-ollama-model-b    running (healthy)
# aim-ai-agent          running (healthy)
# aim-mcp-server        running (healthy)
# aim-flask-ui          running
# aim-target-app        running (healthy)
# aim-chaos-engine      running
# aim-locust            running
```

#### Application Access

- **Flask UI**: http://localhost:8501
- **Locust UI**: http://localhost:8089
- **Target App**: http://localhost:8000/health
- **AI Agent**: http://localhost:8001/health
- **MCP Server**: http://localhost:8002/health

#### Browser Console Verification

Open browser DevTools (F12) → Console tab to verify instrumented logging:

```
[Main] Initializing global utilities
[APIClient] Initialized with baseUrl:
[Main] PollingManager initialized
[Main] DOM loaded, initializing application
[Main] Sidebar polling started (30s interval)
```

**See [Browser Console Logging](#browser-console-logging) section below for detailed documentation.**

#### New Relic Browser Monitoring Verification

**Check APM Dashboard:**
1. Go to New Relic APM
2. Find app: `aim-demo_flask-ui`
3. Verify "Browser" section shows data

**View Browser Transactions:**
- Navigate through all three modes (Repair, Chat, Comparison)
- Click buttons, submit forms, trigger actions
- Check New Relic Browser → Page Views

**AJAX Monitoring:**
Check New Relic Browser → AJAX Requests for polling activity:
- `/api/health` (30s intervals)
- `/api/metrics` (10s intervals)
- `/api/containers` (15s intervals)
- `/api/load-test/status` (5s intervals)

**Browser Script Injection:**
View page source (View → Page Source) and verify New Relic browser script is injected in `<head>`:
```html
<script type="text/javascript">window.NREUM||(NREUM={})...</script>
```

This confirms automatic WSGI instrumentation is working.

### Testing Checklist

#### Repair Mode
- [ ] Container status grid displays 8 containers
- [ ] Container status updates automatically every 15s
- [ ] Model selection works (Model A, Model B, Compare Both)
- [ ] Repair trigger button shows progress spinner
- [ ] Results display with success/failure status
- [ ] Metrics show latency, containers restarted, final status
- [ ] Container logs viewer works for each container
- [ ] Console shows `[Repair]` logs with timing

#### Chat Mode
- [ ] Chat history persists on page refresh
- [ ] Example prompts populate input field
- [ ] Single model responses display correctly
- [ ] Comparison mode shows both responses side-by-side
- [ ] Clear history button removes all messages
- [ ] Session maintains chat across browser refreshes
- [ ] Console shows `[Chat]` logs with message tracking

#### Model Comparison Dashboard
- [ ] Metrics cards display data for both models
- [ ] Metrics auto-update every 10 seconds
- [ ] Plotly latency chart renders with dual lines
- [ ] Plotly success rate chart displays correctly
- [ ] Metrics table populates with request counts
- [ ] Automated insights generate recommendations
- [ ] Export JSON button downloads metrics file
- [ ] Console shows `[Comparison]` logs with timing

#### Load Testing
- [ ] Start load test button triggers test
- [ ] Status updates every 5 seconds when running
- [ ] Stop button appears and works when test active
- [ ] Stats display: total requests, RPS, average response time
- [ ] Console shows `[LoadTest]` logs with status

#### Sidebar (All Pages)
- [ ] Agent status updates every 30 seconds
- [ ] Quick stats show request counts for both models
- [ ] Mode navigation buttons work correctly
- [ ] Resource links open in new tabs
- [ ] Console shows `[Main]` logs for sidebar updates

### Performance Metrics

#### Expected Polling Behavior

| Data | Endpoint | Interval | Log Output |
|------|----------|----------|------------|
| Agent health | `/api/health` | 30s | `[Main] Agent status: Online (uptime: Xh Xm)` |
| Metrics | `/api/metrics` | 10s | `[Comparison] Metrics data: {model_a: {...}, model_b: {...}}` |
| Containers | `/api/containers` | 15s | `[Repair] Found 8 containers` |
| Load test | `/api/load-test/status` | 5s | `[LoadTest] Current status: running, Users: X, RPS: X` |

#### Request Timing

Console logs include performance measurements using `performance.now()`:
```
[APIClient] GET /api/health completed in 45.23ms with status 200
[APIClient] POST /repair/trigger completed in 2543.67ms with status 200
[Repair] Repair workflow completed in 2.54s
[Comparison] Chart update completed in 34.56ms
```

### Success Criteria

✅ **All services healthy:**
```bash
docker-compose ps | grep -c "healthy"
# Should output: 5 (ollama-model-a, ollama-model-b, ai-agent, mcp-server, target-app)
```

✅ **Flask UI accessible:**
```bash
curl -s http://localhost:8501 | grep "<title>AI Monitoring Demo</title>"
```

✅ **Console logging working:**
- Open DevTools (F12) → Console
- See `[Main] Initializing global utilities`
- See polling logs every 5-30 seconds

✅ **AJAX polling active:**
- Check Network tab in DevTools
- See regular requests to `/api/health`, `/api/metrics`, `/api/containers`
- Status codes should be 200

✅ **Charts rendering:**
- Navigate to Model Comparison dashboard
- See two Plotly charts (latency, success rate)
- Charts should update every 10 seconds

✅ **Session persistence:**
- Go to Chat mode
- Send a message
- Refresh the page
- Chat history should remain

✅ **New Relic monitoring:**
- New Relic APM shows `aim-demo_flask-ui` application
- Browser section shows page views
- AJAX requests visible in Browser monitoring
- No JavaScript errors in Browser → JS Errors

## New Relic Integration

### Browser Monitoring
- Automatically instrumented via New Relic APM agent
- `newrelic.ini`: `browser_monitoring.auto_instrument = true`
- No manual JavaScript injection required
- Captures page views, clicks, AJAX requests

### APM Monitoring
- Flask application instrumented via `newrelic-admin run-program`
- Distributed tracing enabled
- Custom AI events for repair workflows and chat interactions

### Key Metrics Captured
- Page load times
- AJAX request performance
- Container status checks
- Repair workflow latency
- Chat interaction latency
- Model comparison metrics
- Load test statistics

## Development Notes

### Adding New Routes
1. Create blueprint in `routes/`
2. Register in `app.py` via `app.register_blueprint()`
3. Create template in `templates/pages/`
4. Add CSS in `static/css/`
5. Add JavaScript in `static/js/`

### JavaScript Architecture
- `main.js` - Global utilities (APIClient, PollingManager, sidebar updates)
- `load_test.js` - Load testing controls
- `repair.js` - Repair mode functionality
- `chat.js` - Chat interface
- `comparison.js` - Dashboard with Plotly charts

### State Management
- Chat history stored in Flask session
- Session lifetime: 24 hours
- Session storage: Filesystem (upgradable to Redis)

## Key Differences from Streamlit

| Feature | Streamlit | Flask |
|---------|-----------|-------|
| Rendering | Auto-rerun | Server-side + AJAX |
| Real-time | Built-in | Manual polling |
| State | session_state | Flask sessions |
| Charts | Python Plotly | Plotly.js (frontend) |
| Deployment | Single process | Gunicorn multi-worker |
| Browser Monitoring | Manual | Automatic (WSGI) |

## Browser Console Logging

The application includes comprehensive instrumented logging for debugging and monitoring. All JavaScript modules output detailed logs with module-specific prefixes and performance timing.

### Log Prefixes
- `[Main]` - Global utilities (APIClient, PollingManager, sidebar updates)
- `[APIClient]` - HTTP requests with timing and response data
- `[Repair]` - Repair mode operations
- `[Chat]` - Chat mode operations
- `[Comparison]` - Dashboard and metrics operations
- `[LoadTest]` - Load testing controls

### Example Console Output
```
[Main] Initializing global utilities
[APIClient] Initialized with baseUrl:
[Main] PollingManager initialized
[Main] DOM loaded, initializing application
[Main] Sidebar polling started (30s interval)
[APIClient] GET request: /api/health
[APIClient] GET /api/health completed in 45.23ms with status 200
[Main] Agent status: Online (uptime: 2h 15m)
[Repair] Initializing repair mode
[Repair] Container status polling started (15s interval)
[Chat] Initializing chat mode
[Chat] Loaded 5 messages from history
[Comparison] Initializing dashboard
[Comparison] Metrics polling started (10s interval)
[LoadTest] Load test controls initialized
```

### Performance Tracking
All API requests include timing information using `performance.now()`:
```
[APIClient] POST /repair/trigger completed in 2543.67ms with status 200
[Repair] Repair workflow completed in 2.54s
[APIClient] GET /api/metrics completed in 123.45ms with status 200
[Comparison] Chart update completed in 45.67ms
```

### Polling Activity
Expected polling logs for each page:
```
# Sidebar (all pages)
[Main] Agent status: Online (uptime: 2h 15m)  # Every 30s

# Repair Mode
[Repair] Found 8 containers  # Every 15s

# Comparison Dashboard
[Comparison] Metrics data: {model_a: {...}, model_b: {...}}  # Every 10s

# Load Test Panel (when running)
[LoadTest] Current status: running, Users: 10, RPS: 25.3  # Every 5s
```

### Debugging Tips
1. **Open DevTools**: Press F12 or right-click → Inspect → Console tab
2. **Filter by Module**: Type `[Repair]` in console filter to see only repair logs
3. **Check Timing**: Look for `completed in Xms` to identify slow requests
4. **Verify Polling**: Confirm you see regular polling logs at expected intervals
5. **Network Tab**: Check Network tab for failed requests (red status codes)
6. **Performance Analysis**: Use timing measurements to identify bottlenecks

## Troubleshooting

### Deployment Issues

#### Container fails to start

**Symptoms:**
- `docker-compose up` exits with error
- Container not listed in `docker-compose ps`

**Solutions:**
```bash
# Check logs for errors
docker-compose logs flask-ui

# Rebuild without cache
docker-compose build --no-cache flask-ui
docker-compose up -d flask-ui

# Verify dependencies are healthy first
docker-compose up -d ai-agent mcp-server
sleep 10
docker-compose up -d flask-ui
```

#### Port 8501 already in use

**Symptoms:**
- Error: "port is already allocated"

**Solutions:**
```bash
# Find and kill process using port
lsof -i :8501
# Kill the PID shown

# Or stop any existing containers
docker-compose down
docker-compose up -d
```

#### Environment variables not loaded

**Symptoms:**
- Container starts but SECRET_KEY warnings in logs
- New Relic not initializing

**Solutions:**
```bash
# Verify .env file exists
ls -la .env

# Check variables are loaded in container
docker exec aim-flask-ui env | grep -E "SECRET_KEY|NEW_RELIC"

# Restart with environment reload
docker-compose down
docker-compose up -d
```

### Application Issues

#### Charts not rendering

**Symptoms:**
- Blank dashboard in Model Comparison mode
- Console error: `[Comparison] Plotly.js not loaded`
- Charts don't update despite polling logs

**Diagnosis:**
```javascript
// In browser console
typeof Plotly
// Should return: "object"
```

**Solutions:**
```bash
# Verify Plotly.js exists
ls -lh flask-ui/static/vendor/plotly-2.27.0.min.js

# Re-download if missing (3.5MB file)
cd flask-ui/static/vendor
curl -o plotly-2.27.0.min.js https://cdn.plot.ly/plotly-2.27.0.min.js

# Rebuild container
docker-compose build --no-cache flask-ui
docker-compose up -d flask-ui
```

### Session not persisting

**Symptoms:**
- Chat history disappears on page refresh
- Console warning about session errors
- User preferences reset

**Diagnosis:**
```bash
# Check session directory exists in container
docker exec aim-flask-ui ls -la /app/flask_session/

# Verify SECRET_KEY is set
docker exec aim-flask-ui env | grep SECRET_KEY
```

**Solutions:**
```bash
# Generate a secure secret key
python3 -c "import os; print(os.urandom(32).hex())"

# Update .env file with new key
# SECRET_KEY=<generated-key>

# Restart container
docker-compose restart flask-ui

# For production: upgrade to Redis sessions
# Update config.py: SESSION_TYPE = 'redis'
```

### New Relic not capturing browser events

**Symptoms:**
- No browser data in New Relic APM dashboard
- Missing "Browser" section in APM
- Page views not tracked

**Diagnosis:**
```bash
# Verify environment variables
docker exec aim-flask-ui env | grep NEW_RELIC

# Check New Relic logs
docker-compose logs flask-ui | grep -i "newrelic\|agent"

# View page source and check for injected script
# Look for: <script type="text/javascript">window.NREUM
```

**Solutions:**
1. **Verify Configuration:**
   - `NEW_RELIC_LICENSE_KEY` is set in `.env`
   - `NEW_RELIC_APP_NAME` is unique (e.g., `aim-demo_flask-ui`)
   - `NEW_RELIC_CONFIG_FILE=/app/newrelic.ini` is set

2. **Check newrelic.ini:**
   ```ini
   [newrelic]
   browser_monitoring.auto_instrument = true
   ```

3. **Verify WSGI startup:**
   ```bash
   # Container should start with newrelic-admin
   docker-compose logs flask-ui | grep "newrelic-admin run-program"
   ```

4. **Restart with fresh build:**
   ```bash
   docker-compose build --no-cache flask-ui
   docker-compose up -d flask-ui
   ```

### AJAX polling not working

**Symptoms:**
- Data doesn't auto-update
- Console shows `[APIClient] GET /api/... failed`
- Network tab shows 500 errors

**Diagnosis:**
```javascript
// In browser console, check polling status
// Should see regular logs like:
[Main] Agent status: Online  // Every 30s
[Repair] Found 8 containers   // Every 15s
[Comparison] Metrics data: {...}  // Every 10s
```

**Solutions:**
```bash
# Check backend services are running
docker-compose ps

# Verify all services healthy
docker-compose ps | grep healthy

# Restart dependencies
docker-compose restart ai-agent mcp-server

# View Flask logs for API errors
docker-compose logs -f flask-ui

# Test API endpoints directly
curl http://localhost:8501/api/health
curl http://localhost:8501/api/containers
curl http://localhost:8501/api/metrics
```

#### Python import errors in container

**Symptoms:**
- `ModuleNotFoundError` in logs
- Container fails health check
- Import errors for Flask or newrelic

**Solutions:**
```bash
# Rebuild with no cache
docker-compose build --no-cache flask-ui

# Check requirements installed
docker exec aim-flask-ui pip list

# Manually test imports
docker exec aim-flask-ui python -c "from app import create_app; print('OK')"
```

## Production Recommendations

### Infrastructure
1. **Redis Sessions**: Upgrade from filesystem to Redis for horizontal scalability
   ```python
   # config.py
   SESSION_TYPE = 'redis'
   SESSION_REDIS = redis.from_url('redis://redis:6379')
   ```

2. **Load Balancer**: Use nginx for multiple Flask instances
   ```nginx
   upstream flask_app {
       server flask-ui-1:8501;
       server flask-ui-2:8501;
       server flask-ui-3:8501;
   }
   ```

3. **Reverse Proxy**: Add nginx for SSL termination and caching
   ```nginx
   location /static/ {
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   ```

### Security
1. **Secrets Management**: Use AWS Secrets Manager, HashiCorp Vault, or similar
   - Never commit `SECRET_KEY` to git
   - Rotate keys regularly
   - Use 32+ byte random keys

2. **Environment Variables**: Inject via orchestration platform
   ```bash
   # Kubernetes ConfigMap/Secret
   # Docker Swarm secrets
   # AWS ECS task definitions
   ```

3. **Session Security**: Enable secure cookies
   ```python
   # config.py (production)
   SESSION_COOKIE_SECURE = True  # HTTPS only
   SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
   SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
   ```

4. **Container Security**: Run as non-root user
   ```dockerfile
   # Add to Dockerfile
   RUN useradd -m -u 1000 flask
   USER flask
   ```

### Monitoring & Observability
1. **New Relic Synthetics**: Add uptime monitoring
   - Monitor critical user journeys
   - Alert on availability issues
   - Track performance SLAs

2. **Application Logs**: Centralize with ELK, Splunk, or CloudWatch
   - Structured logging (JSON format)
   - Log correlation IDs
   - Error tracking and alerting

3. **Metrics Collection**: Add Prometheus metrics
   - Request rates, latencies, error rates
   - Custom business metrics
   - Grafana dashboards

### Performance
1. **Caching Layer**: Add Redis for frequently accessed data
   ```python
   # Cache metrics for 5 seconds
   @cache.memoize(timeout=5)
   def get_metrics():
       return api.get('/api/metrics')
   ```

2. **CDN**: Serve static assets via CloudFront, Fastly, or Cloudflare
   - Cache `/static/` directory
   - Enable gzip compression
   - Use versioned URLs for cache busting

3. **Database Connection Pooling**: If adding persistent storage
   ```python
   # Use SQLAlchemy connection pool
   SQLALCHEMY_POOL_SIZE = 10
   SQLALCHEMY_MAX_OVERFLOW = 20
   ```

### Scalability
1. **Horizontal Scaling**: Run multiple Flask instances
   - Use Docker Swarm, Kubernetes, or ECS
   - Scale based on CPU/memory metrics
   - Implement health checks

2. **Rate Limiting**: Protect API endpoints
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=get_remote_address)

   @limiter.limit("100/minute")
   @app.route('/api/metrics')
   def metrics():
       ...
   ```

3. **Async Workers**: Consider async WSGI server for I/O-bound tasks
   ```bash
   # Replace gunicorn with uvicorn + FastAPI
   # Or use gunicorn with gevent workers
   gunicorn --worker-class gevent --workers 4
   ```

### Security Checklist
- [ ] `SECRET_KEY` is 32+ random bytes from secure source
- [ ] `SECRET_KEY` stored in secrets manager (not `.env` in production)
- [ ] Session cookies have `Secure`, `HttpOnly`, `SameSite` flags
- [ ] HTTPS enforced via reverse proxy
- [ ] CORS configured if using different domains
- [ ] New Relic license key not exposed in logs or errors
- [ ] Container runs as non-root user
- [ ] Security headers set (CSP, X-Frame-Options, etc.)
- [ ] Rate limiting enabled on API endpoints
- [ ] Input validation on all user-provided data
- [ ] Dependencies regularly updated (Dependabot, Renovate)

## License

Built for New Relic AI Monitoring Demo

## Tech Stack

- Flask 3.0.0
- gunicorn 21.2.0
- Plotly.js 2.27.0
- New Relic Python Agent 11.2.0
- requests 2.32.5
- pandas 2.3.3
