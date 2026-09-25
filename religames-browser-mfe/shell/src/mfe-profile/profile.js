import { registerMfe } from '../lib/nr-agent.js';
import * as redeemWidget from './redeem-widget.js';

// Stable entity id -- must match the data-nr-mfe-id on #mfe-profile-root in
// index.html.template so clicks/keys on the drawer are attributed to this MFE.
const PROFILE_ID = 'd8e2b6f4-9a1c-4e5d-8b3a-2c7d6e5f4a3b';

let agent = null;
let rootEl = null;

function renderShell(root, userId) {
  root.hidden = false;
  root.innerHTML = `
    <div class="drawer-header">
      <h2>My Profile</h2>
      <button id="close-profile-btn" type="button" aria-label="Close profile">&times;</button>
    </div>
    <div class="drawer-body">
      <p class="player-tag">${userId || 'guest-player'}</p>

      <h3>Recent Matches</h3>
      <div id="match-list" class="match-list">Loading...</div>

      <div id="redeem-widget-root"></div>

      <h3>Stay in the loop</h3>
      <label class="notify-field">
        Notify me by email
        <input id="notify-email" class="nr-mask" type="email" placeholder="you@example.com" />
      </label>
    </div>
  `;
}

export async function mount(root, { userId, appVersion } = {}) {
  rootEl = root;
  agent = registerMfe(PROFILE_ID, 'ReliGames MFE - Player Profile', { utility: 'Product', internal: false });

  if (userId) agent.setUserId(userId);
  if (appVersion) agent.setApplicationVersion(appVersion);
  agent.log('Player profile opened', { level: 'info', customAttributes: { userId, appVersion } });

  renderShell(root, userId);

  const matchListEl = root.querySelector('#match-list');
  try {
    const res = await fetch('/data/matches.json');
    const matches = await res.json();
    matchListEl.innerHTML = matches
      .map(
        (m) => `
        <div class="match-row" data-match-id="${m.matchId}">
          <span class="mode">${m.mode}</span>
          <span class="result result-${m.result.toLowerCase()}">${m.result}</span>
          <span class="score">${m.score.toLocaleString()}</span>
        </div>`
      )
      .join('');
    agent.log('Match history loaded', { level: 'info', customAttributes: { count: matches.length } });
  } catch (err) {
    agent.log('Match history load failed', {
      level: 'error',
      customAttributes: { message: err.message },
    });
  }

  matchListEl.addEventListener('click', (event) => {
    const row = event.target.closest('.match-row');
    if (!row) return;
    const matchId = row.getAttribute('data-match-id');
    agent.addPageAction('matchViewed', { matchId, userId });
    agent.log('Match viewed', { level: 'debug', customAttributes: { matchId } });
  });

  root.querySelector('#close-profile-btn').addEventListener('click', () => {
    document.dispatchEvent(new CustomEvent('religames:closeProfile'));
  });

  // Nested MFE: registered with `parent` pointing at this MFE's own
  // registration target, so its events attribute up through Player Profile
  // rather than defaulting straight to the container.
  redeemWidget.mount(root.querySelector('#redeem-widget-root'), { agent, userId });
}

export function unmount() {
  redeemWidget.unmount();
  if (agent) {
    agent.log('Player profile closed', { level: 'info' });
    agent.deregister();
    agent = null;
  }
  if (rootEl) {
    rootEl.innerHTML = '';
    rootEl.hidden = true;
  }
  rootEl = null;
}
