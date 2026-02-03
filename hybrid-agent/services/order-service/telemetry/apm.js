/**
 * New Relic APM Instrumentation
 * This must be the first module loaded in the application
 */
'use strict';

const newrelic = require('newrelic');

console.log('New Relic APM initialized for:', process.env.NEW_RELIC_APP_NAME || 'NRDEMO Order Service (APM)');

module.exports = newrelic;
