# Suggested demo talk track (5–10 minutes)

A narrative for showing ReliFarm to a customer. Assumes you've already
deployed via Terraform and `terraform output dashboard_url` resolves.
Adjust depth based on the audience (technical buyer vs. economic buyer
vs. mixed).

---

## Setup checklist (before screen-share)

- [ ] `terraform output dashboard_url` opens in a browser tab; the
      dashboard is loading and showing live data.
- [ ] You're logged into NR in a second browser tab on the same NR
      account the demo deployed under.
- [ ] In NR, pin or open these in tabs in advance so you don't have to
      navigate live:
  * APM & Services → `relifarm-core-engine`
  * Browser → `relifarm-web-dash`
  * Synthetic Monitoring → `relifarm-dashboard-monitor`
  * Errors Inbox (filtered to `relifarm-core-engine`)

If the dashboard tables look stale, click **Trigger Emergency Irrigation**
on a couple of sectors before sharing your screen so the trace data is
fresh.

---

## Act 1 — "What you'd see" (1–2 minutes)

> "ReliFarm is a smart-farm management system. Operators monitor soil
> moisture and temperature across sectors and trigger irrigation when
> conditions hit thresholds. Architecturally it's a distributed system —
> a browser dashboard, two Lambdas behind API Gateway for the irrigation
> chain, and a FastAPI core-engine in front of Postgres. This is the kind
> of multi-service shape that's hard to debug without distributed tracing."

**Show**: the dashboard. Point at the live-updating soil moisture / temp
columns. Click **Trigger Emergency Irrigation** on a sector. The new
execution row appears within a few seconds.

> "Notice the trace_id column on each execution. We'll use that in a minute."

---

## Act 2 — "One trace, four services" (2–3 minutes)

**Switch to NR**: APM & Services → `relifarm-core-engine` → click the
most recent `POST /executions` transaction.

> "This is the trace from the click I just made. Look at the waterfall —
> we're seeing four entities in one trace: the browser, both Lambdas, the
> FastAPI service, and the Postgres database. No agent gymnastics — the
> Browser Agent injected W3C Trace Context headers on its fetch, the
> Lambda Layer continued the trace, the Python APM agent on the
> core-engine continued it again, and psycopg2 spans got auto-attached."

**Highlight one Postgres span**: open it and show the actual SQL.

> "If a customer query is slow, we don't have to guess where — the
> waterfall tells us. Right now most of the time is in the Lambdas
> (cold start) but on a warm trace you'll see the Postgres call dominate."

(If you want to drive the point home, click the trace_id in the dashboard
network response and jump to the exact same trace from a customer-visible
identifier. SEs say this is the moment buyers usually lean in.)

---

## Act 3 — "When things break" (2–3 minutes)

**Show the Errors Inbox** filtered to `relifarm-core-engine`.

> "We've got a synthetic monitor that exercises the irrigation chain
> every 5 minutes and intentionally trips a 500 on about a quarter of
> runs — that's why you see a steady trickle of errors here. Each one's
> stitched into the same trace, so if a synthetic run fails, I get the
> full waterfall + the stack trace + the inbound headers + linked logs,
> all from one entry point."

**Click into a recent error** → show the linked trace, the linked logs
(scroll down on the error detail page), and the affected entity list.

> "This is what 'observability' actually means in practice — one identifier
> connects every signal: trace, logs, errors, the originating user
> session. You're not bouncing between a logging product and an APM
> product and a synthetic product."

---

## Act 4 — "Built once, runs anywhere" (1–2 minutes, optional)

**Show NR Browser**: the `relifarm-web-dash` Browser app overview.

> "Same story on the front end — pageviews, AJAX latency, JS errors,
> the user's geographic distribution, all linked to the same traces
> we just looked at."

**Show NR Synthetic**: the `relifarm-dashboard-monitor`.

> "And the synthetic monitor uses the same Browser Agent, so its runs
> show up in the same traces too. Customers usually want to set this up
> in their CI before deploys land — confirm the critical path works end-
> to-end, in production, every few minutes."

---

## Closing

> "Everything you saw is wired with stock NR agents — no custom
> instrumentation. The core-engine got a `newrelic-admin run-program`
> wrapper, the Lambdas got a published layer, the dashboard got a
> JavaScript snippet. About 15 minutes of integration work, and you get
> all four entities + distributed tracing + errors + synthetics linked
> together for free."

**Hand off to discovery questions** — what does their architecture look
like, where are their current dark spots, what would they want to see
next?

---

## Things to NOT do during the demo

* **Don't open `terraform/` or talk about IaC** unless they ask. The
  AWS plumbing is the cost of the demo, not the value.
* **Don't try to live-edit code.** If they ask "what would custom
  instrumentation look like?", offer to share the repo and walk through
  it after the meeting.
* **Don't claim the synthetic error rate is realistic** — it's 25%
  intentionally. If anyone notices, frame it as "we cranked the
  failure rate up to give you something to look at; in their environment
  they'd set this much lower."
