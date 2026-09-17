// Thin wrapper around New Relic's browser.register() API (see:
// docs-preview.newrelic.com/docs/browser/micro-frontend-monitoring).
// Falls back to a console-logging no-op agent when the container's browser
// agent isn't configured yet, so every MFE can call the same API regardless
// of whether NR instrumentation has been wired up.

export function registerMfe(id, name, tags) {
  const nr = typeof window !== 'undefined' ? window.newrelic : undefined;

  if (nr && typeof nr.register === 'function') {
    try {
      const agent = nr.register({ id, name, tags });
      if (agent) return agent;
    } catch (err) {
      console.warn(`[${name}] newrelic.register() threw, falling back to no-op agent`, err);
    }
  }

  return createNoopAgent(name);
}

function createNoopAgent(name) {
  return {
    setCustomAttribute(key, value) {
      console.debug(`[${name}] setCustomAttribute (noop)`, key, value);
    },
    setUserId(userId) {
      console.debug(`[${name}] setUserId (noop)`, userId);
    },
    setApplicationVersion(version) {
      console.debug(`[${name}] setApplicationVersion (noop)`, version);
    },
    addPageAction(actionName, attributes) {
      console.debug(`[${name}] addPageAction (noop)`, actionName, attributes);
    },
    noticeError(error, attributes) {
      console.error(`[${name}] noticeError (noop)`, error, attributes);
    },
    log(message, opts) {
      const level = (opts && opts.level) || 'info';
      const fn = level === 'error' ? console.error : level === 'warn' ? console.warn : console.log;
      fn(`[${name}]`, message, (opts && opts.customAttributes) || '');
    },
    recordCustomEvent(eventType, attributes) {
      console.debug(`[${name}] recordCustomEvent (noop)`, eventType, attributes);
    },
    measure(measureName, timing) {
      console.debug(`[${name}] measure (noop)`, measureName, timing);
    },
    deregister() {
      console.debug(`[${name}] deregister (noop)`);
    },
  };
}
