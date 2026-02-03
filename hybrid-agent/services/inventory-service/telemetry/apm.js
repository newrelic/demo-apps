/**
 * New Relic APM Instrumentation for Inventory Service
 */
'use strict';

const newrelic = require('newrelic');

console.log('New Relic APM initialized for:', process.env.NEW_RELIC_APP_NAME || 'NRDEMO Inventory Service (APM)');

module.exports = newrelic;
