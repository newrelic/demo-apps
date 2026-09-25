// Host/"container" page logic. It doesn't register itself as an MFE, but it
// does use two container-level APIs: the global newrelic.setCustomAttribute
// (below) and, for demo purposes only, registerMfe() to intentionally
// collide with the Leaderboard MFE's id/name (see initMisconfigurationDemo).

import { registerMfe } from './lib/nr-agent.js';

function getQueryParam(name, fallback) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || fallback;
}

const userId = getQueryParam('uid', 'guest-player');
const appVersion = getQueryParam('ver', '2.4.0');

// Must match LEADERBOARD_ID in mfe-leaderboard/leaderboard.js -- reused below
// to demonstrate an id/name collision, not to register a real MFE here.
const LEADERBOARD_ID = 'a3f1c2d0-4b3e-4b7a-9c1d-1f2e3a4b5c6d';

function mountLeaderboard() {
  const root = document.getElementById('mfe-leaderboard-root');
  if (root && window.ReliGamesLeaderboard) {
    window.ReliGamesLeaderboard.mount(root, { userId, appVersion });
  }
}

function initProfileToggle() {
  const toggleBtn = document.getElementById('profile-toggle-btn');
  const drawer = document.getElementById('mfe-profile-root');
  let open = false;

  function openProfile() {
    if (open || !window.ReliGamesProfile) return;
    open = true;
    toggleBtn.textContent = 'Close Profile';
    window.ReliGamesProfile.mount(drawer, { userId, appVersion });
  }

  function closeProfile() {
    if (!open || !window.ReliGamesProfile) return;
    open = false;
    toggleBtn.textContent = 'My Profile';
    window.ReliGamesProfile.unmount();
  }

  toggleBtn.addEventListener('click', () => (open ? closeProfile() : openProfile()));
  document.addEventListener('religames:closeProfile', closeProfile);
}

function initAppErrorButton() {
  // Deliberately outside both MFEs' data-nr-mfe-id subtrees, and this file
  // never calls newrelic.register() -- an uncaught error thrown from here
  // is attributed to the container application, not either MFE.
  document.getElementById('simulate-app-error-btn').addEventListener('click', () => {
    throw new Error('Simulated container-level application error (outside any MFE)');
  });
}

function initGlobalCustomAttribute() {
  // The global newrelic.setCustomAttribute (3rd arg = persist across page
  // loads in this session) fans out to every exposed, non-Micro agent
  // instance on the page -- unlike the register()-scoped
  // agent.setCustomAttribute calls in the Leaderboard/Redeem Widget, which
  // are local to that one registered entity's own attrs bag.
  if (typeof window.newrelic?.setCustomAttribute === 'function') {
    window.newrelic.setCustomAttribute('appVersion', appVersion, true);
  }
}

function initMisconfigurationDemo() {
  const btn = document.getElementById('simulate-mfe-collision-btn');
  if (!btn) return;

  btn.addEventListener('click', () => {
    // Each warning code is only ever printed once per page load (the agent
    // wraps them in a `single()` guard), so clicking this more than once
    // won't repeat the console output below -- that's expected.
    console.info('--- Simulating same-name/different-id collision (expect warning #81) ---');
    const nameCollision = registerMfe(crypto.randomUUID(), 'ReliGames MFE - Leaderboard', {});

    console.info('--- Simulating same-id/different-name collision (expect warning #82) ---');
    const idCollision = registerMfe(LEADERBOARD_ID, 'Not The Real Leaderboard', {});

    // These are demo-only registrations -- deregister immediately so they
    // don't pollute the real Leaderboard MFE's ongoing telemetry.
    nameCollision.deregister();
    idCollision.deregister();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  mountLeaderboard();
  initProfileToggle();
  initAppErrorButton();
  initGlobalCustomAttribute();
  initMisconfigurationDemo();
});
