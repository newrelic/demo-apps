import { registerMfe } from '../lib/nr-agent.js';

// Stable entity id -- must match the data-nr-mfe-id set on #redeem-widget-root
// below. Registered with `parent` set to the Player Profile MFE's own
// registration target (see mount()), nesting this widget one level under it
// (type "MFE" -> parent type "MFE" -> grandparent type "BA" for the
// container) instead of defaulting straight to the container.
const REDEEM_WIDGET_ID = '5f6a7b8c-1d2e-4f3a-9b8c-7d6e5f4a3b2c';

const VALID_REWARD_CODES = new Set(['RELIGAMES2026', 'LEVELUP', 'MVPWEEK']);

let agent = null;
let rootEl = null;

function render(root) {
  root.setAttribute('data-nr-mfe-id', REDEEM_WIDGET_ID);
  root.innerHTML = `
    <h3>Redeem Reward Code</h3>
    <form id="redeem-form">
      <input id="redeem-code" type="text" placeholder="Enter code" autocomplete="off" />
      <button type="submit">Redeem</button>
    </form>
    <p id="redeem-status"></p>
  `;
}

export function mount(root, { agent: parentAgent, userId } = {}) {
  rootEl = root;
  agent = registerMfe(
    REDEEM_WIDGET_ID,
    'ReliGames MFE - Reward Redeem Widget',
    { utility: 'Product', internal: false },
    { parent: parentAgent?.metadata?.target }
  );

  render(root);

  const redeemForm = root.querySelector('#redeem-form');
  const redeemStatus = root.querySelector('#redeem-status');

  redeemForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const code = root.querySelector('#redeem-code').value.trim().toUpperCase();
    agent.addPageAction('rewardCodeSubmitted', { code, userId });
    agent.log('Reward code submitted', { level: 'info', customAttributes: { code } });

    try {
      if (!code) {
        throw new Error('Reward code cannot be empty');
      }
      if (!VALID_REWARD_CODES.has(code)) {
        throw new Error(`Invalid reward code: ${code}`);
      }

      // register()-scoped setCustomAttribute writes to this widget's own,
      // local attrs bag (shows up as source.* on its own events) -- a
      // different code path from the global newrelic.setCustomAttribute in
      // shell.js, which instead fans out to every exposed agent instance on
      // the page.
      agent.setCustomAttribute('rewardTier', code);
      agent.recordCustomEvent('RewardRedeemed', { code, userId });
      agent.log('Reward code redeemed', { level: 'info', customAttributes: { code } });
      redeemStatus.textContent = 'Reward redeemed! Check your inventory.';
      redeemStatus.className = 'status-success';
    } catch (err) {
      // Purposeful error (2 of 2 in the app): explicit try/catch + noticeError,
      // contrasting with the Leaderboard's uncaught/automatic error path.
      // Emitted from this nested widget, it also demonstrates the full
      // parent chain (widget -> Player Profile MFE -> container) via the
      // parent.id/parent.type attributes New Relic attaches to the event.
      agent.noticeError(err, { context: 'reward-redeem', code });
      agent.log('Reward code rejected', {
        level: 'warn',
        customAttributes: { code, message: err.message },
      });
      redeemStatus.textContent = err.message;
      redeemStatus.className = 'status-error';
    }
  });
}

export function unmount() {
  if (agent) {
    agent.log('Redeem widget closed', { level: 'info' });
    agent.deregister();
    agent = null;
  }
  if (rootEl) {
    rootEl.innerHTML = '';
  }
  rootEl = null;
}
