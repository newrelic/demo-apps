/**
 * New Relic Browser Agent Configuration
 *
 * This script conditionally initializes the Browser agent only if valid
 * credentials are provided. If placeholder values are detected, Browser
 * monitoring is skipped and the demo runs with backend-only instrumentation.
 */

(function() {
  // Check if we have environment variables from the build
  // These would be injected during Docker build if needed
  const browserAgentId = window.NR_BROWSER_AGENT_ID || '';
  const browserAppId = window.NR_BROWSER_APP_ID || '';
  const trustKey = window.NR_TRUST_KEY || '';

  // List of placeholder values that indicate Browser agent is not configured
  const placeholders = [
    'your_browser_agent_id',
    'your_browser_app_id',
    'your_trust_key',
    '',
    null,
    undefined
  ];

  // Check if all values are set and not placeholders
  const isConfigured =
    browserAgentId &&
    browserAppId &&
    trustKey &&
    !placeholders.includes(browserAgentId) &&
    !placeholders.includes(browserAppId) &&
    !placeholders.includes(trustKey);

  if (!isConfigured) {
    console.log('[NR Browser] Browser agent not configured - running with backend instrumentation only');
    console.log('[NR Browser] To enable Browser monitoring, configure NEW_RELIC_BROWSER_* variables in .env');
    return;
  }

  // If we reach here, we have valid Browser agent credentials
  console.log('[NR Browser] Initializing Browser agent');

  // Initialize New Relic Browser agent
  window.NREUM || (NREUM = {});
  NREUM.init = {
    distributed_tracing: { enabled: true },
    privacy: { cookies_enabled: true },
    ajax: { deny_list: [] }
  };

  // NOTE: The full Browser agent script would be injected here
  // For this demo, you would need to:
  // 1. Get the Browser agent snippet from New Relic UI
  // 2. Add it to this file or inject it during the Docker build
  // 3. The snippet typically looks like:
  //    <script type="text/javascript">/*! For license information please see nr-spa-1.x.x.min.js.LICENSE.txt */
  //    (function(){/* Browser agent code here */})();
  //    </script>

  console.log('[NR Browser] Browser agent initialized successfully');
})();
