/* =============================================================================
 * ReliFarm — dashboard JS
 *
 * Polls the core-engine for sector/tractor telemetry every 4 s. Emergency
 * irrigation goes through the yield-forecast Lambda; the New Relic Browser
 * Agent (loaded in <head>) auto-injects W3C `traceparent` headers on fetch
 * calls when distributed-tracing-on-fetch is enabled in the browser app
 * config (Terraform sets `distributed_tracing.enabled = true`).
 * ============================================================================= */

const CONFIG = window.RELIFARM_CONFIG || {};
const POLL_INTERVAL_MS = 4000;

const els = {
    connection: document.getElementById("connectionStatus"),
    kpiMoisture: document.getElementById("kpiMoisture"),
    kpiTemp: document.getElementById("kpiTemp"),
    kpiValves: document.getElementById("kpiValves"),
    kpiTractors: document.getElementById("kpiTractors"),
    sectorBody: document.querySelector("#sectorTable tbody"),
    tractorBody: document.querySelector("#tractorTable tbody"),
    executionBody: document.querySelector("#executionTable tbody"),
    toast: document.getElementById("toast"),
};

// --- toast helpers ---------------------------------------------------------
let toastTimer = null;
function toast(message, kind = "") {
    els.toast.textContent = message;
    els.toast.className = `toast show ${kind}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { els.toast.className = "toast"; }, 4000);
}

// --- fetch helpers ---------------------------------------------------------
async function fetchJSON(url, options = {}) {
    const resp = await fetch(url, options);
    if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(`HTTP ${resp.status} ${resp.statusText} — ${text}`);
    }
    return resp.json();
}

// --- rendering -------------------------------------------------------------
function renderSectors(sectors) {
    els.sectorBody.innerHTML = sectors.map(s => {
        const moistureClass = s.soil_moisture_pct < 30 ? "moisture-low"
                            : s.soil_moisture_pct > 60 ? "moisture-high"
                            : "";
        return `
            <tr>
                <td>${s.sector_id}</td>
                <td>${s.crop_type}</td>
                <td>${Number(s.area_hectares).toFixed(1)}</td>
                <td class="${moistureClass}">${Number(s.soil_moisture_pct).toFixed(1)}</td>
                <td>${Number(s.soil_temp_c).toFixed(1)}</td>
                <td class="${s.valve_open ? "valve-on" : "valve-off"}">${s.valve_open ? "OPEN" : "closed"}</td>
                <td>
                    <button class="action" data-sector="${s.sector_id}" data-moisture="${s.soil_moisture_pct}" data-temp="${s.soil_temp_c}" data-area="${s.area_hectares}">
                        Trigger Emergency Irrigation
                    </button>
                </td>
            </tr>`;
    }).join("");

    els.sectorBody.querySelectorAll("button.action").forEach(btn => {
        btn.addEventListener("click", () => triggerEmergencyIrrigation(btn));
    });

    const moistureAvg = sectors.reduce((acc, s) => acc + Number(s.soil_moisture_pct), 0) / Math.max(1, sectors.length);
    const tempAvg = sectors.reduce((acc, s) => acc + Number(s.soil_temp_c), 0) / Math.max(1, sectors.length);
    const valveCount = sectors.filter(s => s.valve_open).length;

    els.kpiMoisture.textContent = `${moistureAvg.toFixed(1)}%`;
    els.kpiTemp.textContent = `${tempAvg.toFixed(1)} °C`;
    els.kpiValves.textContent = `${valveCount} / ${sectors.length}`;
}

function renderTractors(tractors) {
    els.tractorBody.innerHTML = tractors.map(t => `
        <tr>
            <td>${t.tractor_id}</td>
            <td>${Number(t.latitude).toFixed(5)}</td>
            <td>${Number(t.longitude).toFixed(5)}</td>
            <td>${Number(t.fuel_pct).toFixed(1)}</td>
            <td>${t.status}</td>
        </tr>
    `).join("");
    els.kpiTractors.textContent = `${tractors.length}`;
}

function renderExecutions(executions) {
    els.executionBody.innerHTML = executions.map(e => `
        <tr>
            <td>${new Date(e.executed_at).toLocaleTimeString()}</td>
            <td>${e.sector_id}</td>
            <td>${e.triggered_by}</td>
            <td>${Number(e.yield_health).toFixed(1)}</td>
            <td>${Number(e.water_volume_l).toFixed(0)}</td>
            <td>${e.duration_seconds}</td>
        </tr>
    `).join("");
}

// --- main loop -------------------------------------------------------------
async function refresh() {
    try {
        const [sectors, tractors, executions] = await Promise.all([
            fetchJSON(`${CONFIG.coreEngineUrl}/sectors`),
            fetchJSON(`${CONFIG.coreEngineUrl}/tractors`),
            fetchJSON(`${CONFIG.coreEngineUrl}/executions?limit=12`),
        ]);
        renderSectors(sectors);
        renderTractors(tractors);
        renderExecutions(executions);
        els.connection.textContent = "live";
        els.connection.className = "status-pill online";
    } catch (err) {
        console.error("refresh failed", err);
        els.connection.textContent = "offline";
        els.connection.className = "status-pill offline";
        if (window.newrelic) window.newrelic.noticeError(err);
    }
}

// --- emergency irrigation --------------------------------------------------
async function triggerEmergencyIrrigation(btn) {
    const payload = {
        sector_id: btn.dataset.sector,
        soil_moisture_pct: Number(btn.dataset.moisture),
        soil_temp_c: Number(btn.dataset.temp),
        area_hectares: Number(btn.dataset.area),
        triggered_by: "manual",
    };

    btn.disabled = true;
    btn.textContent = "Sending…";

    if (window.newrelic) {
        window.newrelic.addPageAction("emergency_irrigation_clicked", {
            sector_id: payload.sector_id,
            moisture: payload.soil_moisture_pct,
        });
    }

    try {
        const resp = await fetch(CONFIG.yieldForecastUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const body = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status} — ${JSON.stringify(body)}`);
        }
        toast(`Irrigation queued for ${payload.sector_id}`, "success");
    } catch (err) {
        console.error("emergency irrigation failed", err);
        toast(`Failed: ${err.message}`, "error");
        if (window.newrelic) window.newrelic.noticeError(err);
    } finally {
        btn.disabled = false;
        btn.textContent = "Trigger Emergency Irrigation";
    }
}

refresh();
setInterval(refresh, POLL_INTERVAL_MS);
