import { registerMfe } from '../lib/nr-agent.js';

// Stable entity id -- must match the data-nr-mfe-id on #mfe-leaderboard-root
// in index.html.template so clicks/keys are attributed to this MFE, and so
// vitals.fcp.value is captured from first paint rather than after mount.
const LEADERBOARD_ID = 'a3f1c2d0-4b3e-4b7a-9c1d-1f2e3a4b5c6d';

let agent = null;
let rootEl = null;

function renderShell(root) {
  root.innerHTML = `
    <div class="panel-header">
      <h2>Live Leaderboard</h2>
      <div class="panel-actions">
        <input id="leaderboard-search" type="search" placeholder="Search player or team..." />
        <button id="refresh-rankings-btn" type="button">Refresh Rankings</button>
      </div>
    </div>
    <div id="leaderboard-list" class="leaderboard-list">Loading rankings...</div>
  `;
}

function renderRows(listEl, players, filterText) {
  const needle = (filterText || '').trim().toLowerCase();
  const filtered = needle
    ? players.filter(
        (p) => p.playerName.toLowerCase().includes(needle) || p.team.toLowerCase().includes(needle)
      )
    : players;

  if (!filtered.length) {
    listEl.innerHTML = '<p class="empty-state">No players match your search.</p>';
    return;
  }

  listEl.innerHTML = filtered
    .map(
      (p) => `
      <div class="leaderboard-row" data-player-id="${p.playerName}">
        <span class="rank">#${p.rank}</span>
        <span class="player">${p.playerName}</span>
        <span class="team">${p.team}</span>
        <span class="region">${p.region}</span>
        <span class="score">${p.score.toLocaleString()}</span>
      </div>`
    )
    .join('');
}

export async function mount(root, { userId, appVersion } = {}) {
  rootEl = root;
  agent = registerMfe(LEADERBOARD_ID, 'Leaderboard', { utility: 'Product', internal: false });

  if (userId) agent.setUserId(userId);
  if (appVersion) agent.setApplicationVersion(appVersion);
  agent.log('Leaderboard mounting', { level: 'info', customAttributes: { userId, appVersion } });

  const renderStart = performance.now();
  renderShell(root);

  const searchInput = root.querySelector('#leaderboard-search');
  const refreshBtn = root.querySelector('#refresh-rankings-btn');
  const listEl = root.querySelector('#leaderboard-list');

  let players = [];
  try {
    const res = await fetch('/data/leaderboard.json');
    players = await res.json();
    agent.log('Leaderboard data loaded', { level: 'info', customAttributes: { count: players.length } });
  } catch (err) {
    agent.log('Leaderboard data load failed', {
      level: 'error',
      customAttributes: { message: err.message },
    });
  }

  renderRows(listEl, players, '');
  agent.measure('leaderboard-render', { start: renderStart, end: performance.now() });

  searchInput.addEventListener('input', (event) => {
    renderRows(listEl, players, event.target.value);
    agent.log('Leaderboard search updated', {
      level: 'debug',
      customAttributes: { query: event.target.value },
    });
  });

  listEl.addEventListener('click', (event) => {
    const row = event.target.closest('.leaderboard-row');
    if (!row) return;
    const playerId = row.getAttribute('data-player-id');
    agent.addPageAction('playerViewed', { playerId, userId });
    agent.log('Player row viewed', { level: 'debug', customAttributes: { playerId } });
  });

  refreshBtn.addEventListener('click', () => {
    agent.log('Refresh rankings requested', { level: 'info', customAttributes: { userId } });

    // Purposeful error (1 of 2 in the app): simulated rankings-sync failure,
    // left uncaught on purpose so the Browser agent's automatic stack-trace
    // attribution (rather than an explicit noticeError call) picks it up.
    if (Math.random() < 0.34) {
      throw new Error('Rankings sync failed: leaderboard service timeout');
    }

    renderRows(listEl, players, searchInput.value);
    agent.log('Rankings refreshed', { level: 'info' });
  });
}

export function unmount() {
  if (agent) {
    agent.log('Leaderboard unmounting', { level: 'info' });
    agent.deregister();
    agent = null;
  }
  if (rootEl) {
    rootEl.innerHTML = '';
  }
  rootEl = null;
}

// The leaderboard stays mounted for the whole page view; deregister when the
// page is actually going away (covers reload, navigation, and tab close).
window.addEventListener('pagehide', unmount);
