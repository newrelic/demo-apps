// Host/"container" page logic. This file does not itself call
// newrelic.register() -- it just mounts the two micro frontends (each of
// which registers itself) and wires up the profile-drawer toggle.

function getQueryParam(name, fallback) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || fallback;
}

const userId = getQueryParam('uid', 'guest-player');
const appVersion = getQueryParam('ver', '2.4.0');

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

document.addEventListener('DOMContentLoaded', () => {
  mountLeaderboard();
  initProfileToggle();
  initAppErrorButton();
});
