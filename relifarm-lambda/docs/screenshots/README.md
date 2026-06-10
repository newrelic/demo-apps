# Screenshots — what to capture

This directory is a placeholder. The main README references screenshots
at the spots where they'd most help an SE land a demo, but the images
themselves aren't in the repo yet.

If you've deployed ReliFarm and want to contribute, capture the shots
below at native resolution (no compression, no annotation overlays — let
the SE annotate live during their demo).

---

## Recommended captures

### 1. `dashboard.png` — the live dashboard

* Open `terraform output dashboard_url` in a clean browser window
  (no extensions, no DevTools panel open).
* Wait until at least two sectors have a recent value in the
  "Recent irrigation executions" table.
* Capture the full dashboard above the fold. Include the trace_id column.

### 2. `apm-entities.png` — NR APM service list

* In NR → **APM & Services**, filter to entities prefixed `relifarm-`.
* All three should be visible: `relifarm-core-engine`,
  `relifarm-yield-forecast`, `relifarm-valve-scheduler`.
* Capture the list view showing throughput sparklines.

### 3. `distributed-trace.png` — the four-hop waterfall

* Trigger an irrigation run from the dashboard.
* In NR → APM & Services → `relifarm-core-engine` → click the most
  recent `POST /executions`.
* Capture the Distributed Tracing waterfall with all four entities
  visible. The Postgres span at the bottom is the punchline — make
  sure it's in frame.

### 4. `errors-inbox.png` (optional)

* In NR → **Errors Inbox**, filter to entity = `relifarm-core-engine`.
* Capture the inbox after the synthetic monitor has tripped at least
  one error-injection run (~5 minutes after first apply).

### 5. `browser-app.png` (optional)

* In NR → Browser → `relifarm-web-dash` overview.
* Capture the page-views chart + AJAX latency chart.

---

## Where they'd be referenced

`README.md` contains TODO comments at the spots where each screenshot
would land. Search the README for `TODO screenshots` to find them.

When adding screenshots, update the README to reference them inline,
e.g.:

```markdown
![Dashboard](docs/screenshots/dashboard.png)
```
