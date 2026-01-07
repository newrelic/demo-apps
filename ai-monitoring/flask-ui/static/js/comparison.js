// Dashboard and Charts Functionality

console.log('[Comparison] Initializing comparison dashboard');

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Comparison] DOM loaded, setting up dashboard');
    // Auto-refresh metrics every 10 seconds
    polling.start('metrics', updateMetrics, 10000);
    console.log('[Comparison] Metrics polling started (10s interval)');

    // Manual refresh button
    document.getElementById('refresh-metrics-btn').addEventListener('click', () => {
        console.log('[Comparison] Manual refresh triggered');
        updateMetrics();
    });

    // Export button
    document.getElementById('export-json-btn').addEventListener('click', () => {
        console.log('[Comparison] Export metrics triggered');
        exportMetrics();
    });

    console.log('[Comparison] Event listeners configured');
});

async function updateMetrics() {
    console.log('[Comparison] Updating metrics dashboard');
    try {
        const data = await api.get('/api/metrics');

        if (data.error) {
            console.error('[Comparison] Error fetching metrics:', data.error);
            return;
        }

        const modelA = data.model_a;
        const modelB = data.model_b;

        console.log('[Comparison] Metrics data:', {
            modelA: { requests: modelA.total_requests, success: modelA.success_rate },
            modelB: { requests: modelB.total_requests, success: modelB.success_rate }
        });

        // Update overview cards
        document.querySelector('#model-a-requests .metric-value').textContent = modelA.total_requests;
        document.querySelector('#model-a-success .metric-value').textContent =
            `${(modelA.success_rate * 100).toFixed(1)}%`;
        document.querySelector('#model-b-requests .metric-value').textContent = modelB.total_requests;
        document.querySelector('#model-b-success .metric-value').textContent =
            `${(modelB.success_rate * 100).toFixed(1)}%`;

        // Update detailed comparison
        updateDetailedComparison(modelA, modelB);

        // Update charts
        updateLatencyChart(modelA, modelB);
        updateSuccessChart(modelA, modelB);

        // Update table
        updateComparisonTable(modelA, modelB);

        // Generate insights
        generateInsights(modelA, modelB);

        console.log('[Comparison] Dashboard updated successfully');

    } catch (error) {
        console.error('[Comparison] Error updating metrics:', error);
    }
}

function updateDetailedComparison(modelA, modelB) {
    document.getElementById('model-a-details').innerHTML = `
        <div class="detail-item">Model: ${modelA.name}</div>
        <div class="detail-item">Total Requests: ${modelA.total_requests}</div>
        <div class="detail-item">Successful: ${modelA.successful_requests}</div>
        <div class="detail-item">Failed: ${modelA.failed_requests}</div>
        <div class="detail-item">Avg Latency: ${modelA.avg_latency_seconds.toFixed(2)}s</div>
    `;

    document.getElementById('model-b-details').innerHTML = `
        <div class="detail-item">Model: ${modelB.name}</div>
        <div class="detail-item">Total Requests: ${modelB.total_requests}</div>
        <div class="detail-item">Successful: ${modelB.successful_requests}</div>
        <div class="detail-item">Failed: ${modelB.failed_requests}</div>
        <div class="detail-item">Avg Latency: ${modelB.avg_latency_seconds.toFixed(2)}s</div>
    `;
}

function updateLatencyChart(modelA, modelB) {
    console.log('[Comparison] Updating latency chart');
    if (typeof Plotly === 'undefined') {
        console.error('[Comparison] Plotly.js not loaded');
        document.getElementById('latency-chart').innerHTML =
            '<div class="error">Plotly.js not loaded. Charts unavailable.</div>';
        return;
    }

    const data = [
        {
            x: ['Average Latency'],
            y: [modelA.avg_latency_seconds],
            name: 'Model A',
            type: 'bar',
            marker: { color: '#0066cc' }
        },
        {
            x: ['Average Latency'],
            y: [modelB.avg_latency_seconds],
            name: 'Model B',
            type: 'bar',
            marker: { color: '#00c9a7' }
        }
    ];

    const layout = {
        title: 'Average Response Latency (seconds)',
        yaxis: { title: 'Seconds' },
        barmode: 'group',
        height: 400
    };

    Plotly.newPlot('latency-chart', data, layout);
}

function updateSuccessChart(modelA, modelB) {
    console.log('[Comparison] Updating success rate chart');
    if (typeof Plotly === 'undefined') {
        console.error('[Comparison] Plotly.js not loaded');
        document.getElementById('success-chart').innerHTML =
            '<div class="error">Plotly.js not loaded. Charts unavailable.</div>';
        return;
    }

    const successA = (modelA.success_rate * 100).toFixed(1);
    const successB = (modelB.success_rate * 100).toFixed(1);

    const data = [
        {
            x: ['Success Rate'],
            y: [successA],
            name: 'Model A',
            type: 'bar',
            marker: { color: '#0066cc' },
            text: [`${successA}%`],
            textposition: 'auto'
        },
        {
            x: ['Success Rate'],
            y: [successB],
            name: 'Model B',
            type: 'bar',
            marker: { color: '#00c9a7' },
            text: [`${successB}%`],
            textposition: 'auto'
        }
    ];

    const layout = {
        title: 'Success Rate Percentage',
        yaxis: { title: 'Percentage', range: [0, 100] },
        barmode: 'group',
        height: 400
    };

    Plotly.newPlot('success-chart', data, layout);
}

function updateComparisonTable(modelA, modelB) {
    const tbody = document.querySelector('#comparison-table tbody');
    const successA = (modelA.success_rate * 100).toFixed(1);
    const successB = (modelB.success_rate * 100).toFixed(1);

    tbody.innerHTML = `
        <tr><td>Model Name</td><td>${modelA.name}</td><td>${modelB.name}</td></tr>
        <tr><td>Total Requests</td><td>${modelA.total_requests}</td><td>${modelB.total_requests}</td></tr>
        <tr><td>Successful Requests</td><td>${modelA.successful_requests}</td><td>${modelB.successful_requests}</td></tr>
        <tr><td>Failed Requests</td><td>${modelA.failed_requests}</td><td>${modelB.failed_requests}</td></tr>
        <tr><td>Success Rate</td><td>${successA}%</td><td>${successB}%</td></tr>
        <tr><td>Avg Latency (s)</td><td>${modelA.avg_latency_seconds.toFixed(2)}</td><td>${modelB.avg_latency_seconds.toFixed(2)}</td></tr>
    `;
}

function generateInsights(modelA, modelB) {
    const insightsContent = document.getElementById('insights-content');

    if (modelA.total_requests === 0 && modelB.total_requests === 0) {
        insightsContent.innerHTML = '<p>📊 No metrics available yet. Run some repair workflows or chat interactions.</p>';
        return;
    }

    let insights = '<div class="insights-grid">';

    // Speed comparison
    if (modelA.avg_latency_seconds < modelB.avg_latency_seconds) {
        const advantage = ((modelB.avg_latency_seconds - modelA.avg_latency_seconds) / modelB.avg_latency_seconds * 100).toFixed(1);
        insights += `<div class="insight speed">⚡ Model A is ${advantage}% faster than Model B</div>`;
    } else if (modelB.avg_latency_seconds < modelA.avg_latency_seconds) {
        const advantage = ((modelA.avg_latency_seconds - modelB.avg_latency_seconds) / modelA.avg_latency_seconds * 100).toFixed(1);
        insights += `<div class="insight speed">⚡ Model B is ${advantage}% faster than Model A</div>`;
    }

    // Accuracy comparison
    const successA = modelA.success_rate * 100;
    const successB = modelB.success_rate * 100;

    if (successA > successB) {
        insights += `<div class="insight accuracy">🎯 Model A has a ${(successA - successB).toFixed(1)}% higher success rate</div>`;
    } else if (successB > successA) {
        insights += `<div class="insight accuracy">🎯 Model B has a ${(successB - successA).toFixed(1)}% higher success rate</div>`;
    }

    insights += '</div>';

    // Recommendation
    if (modelA.total_requests >= 3 && modelB.total_requests >= 3) {
        insights += '<div class="recommendation">';
        if (successA >= 95 && successB >= 95) {
            if (modelA.avg_latency_seconds < modelB.avg_latency_seconds) {
                insights += '✅ <strong>Use Model A</strong> for cost-effective, high-performance repairs with fast response times.';
            } else {
                insights += '✅ <strong>Use Model B</strong> for maximum reliability.';
            }
        } else if (successA > successB) {
            insights += '✅ <strong>Use Model A</strong> - Better success rate and faster responses.';
        } else if (successB > successA) {
            insights += '✅ <strong>Use Model B</strong> - Higher success rate justifies additional latency.';
        } else {
            insights += '⚖️ <strong>Both models perform similarly</strong> - Choose based on cost and latency requirements.';
        }
        insights += '</div>';
    } else {
        insights += '<div class="recommendation warning">⏳ More data needed for accurate recommendations. Run more repair workflows.</div>';
    }

    insightsContent.innerHTML = insights;
}

async function exportMetrics() {
    console.log('[Comparison] Exporting metrics to JSON');
    try {
        const data = await api.get('/api/metrics');
        const dataStr = JSON.stringify(data, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = 'model_comparison_metrics.json';
        a.click();

        URL.revokeObjectURL(url);
        console.log('[Comparison] Metrics exported successfully');
    } catch (error) {
        console.error('[Comparison] Export failed:', error);
        alert(`Error exporting metrics: ${error.message}`);
    }
}
