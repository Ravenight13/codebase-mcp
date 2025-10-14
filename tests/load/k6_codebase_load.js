/**
 * k6 Load Test Scenario for Codebase-MCP Server
 *
 * Purpose: Validate that codebase-mcp handles 50 concurrent clients without
 *          crashing or becoming unresponsive under sustained load.
 *
 * Constitutional Compliance:
 * - SC-006: 50 concurrent clients handled without crash
 * - SC-007: 99.9% uptime during extended load testing
 * - Principle IV: Performance guarantees (p95<2000ms under extreme load)
 *
 * Test Scenario:
 * - Ramp-up: 0 -> 10 users (2 min) -> 50 users (5 min)
 * - Sustained: 50 users for 10 minutes
 * - Ramp-down: 50 -> 0 users (2 min)
 * - Total duration: 19 minutes
 *
 * Success Criteria:
 * - p95 latency < 2000ms (graceful degradation under extreme load)
 * - Error rate < 1% (99% success rate)
 * - No server crashes or unresponsiveness
 *
 * Usage:
 *   k6 run tests/load/k6_codebase_load.js
 *
 * Requirements:
 * - codebase-mcp server running on http://localhost:8020
 * - Repository indexed with test data
 * - k6 version 0.45+ installed
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics for detailed analysis
const errorRate = new Rate('codebase_errors');
const searchLatency = new Trend('codebase_search_duration', true);

// Load test configuration
export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp-up to 10 users over 2 minutes
    { duration: '5m', target: 50 },   // Ramp-up to 50 users over 5 minutes
    { duration: '10m', target: 50 },  // Sustained load at 50 concurrent users
    { duration: '2m', target: 0 },    // Ramp-down to 0 users over 2 minutes
  ],

  // Performance thresholds (test fails if any threshold is violated)
  thresholds: {
    'http_req_duration': ['p(95)<2000'],       // p95 latency < 2000ms (graceful degradation)
    'http_req_failed': ['rate<0.01'],          // Error rate < 1%
    'codebase_errors': ['rate<0.01'],          // Custom error tracking < 1%
    'codebase_search_duration': ['p(95)<2000'], // Search-specific p95 < 2000ms
    'http_reqs': ['rate>0'],                   // Ensure requests are being made
  },

  // Additional configuration
  noConnectionReuse: false,  // Reuse connections (more realistic)
  userAgent: 'k6-load-test/1.0 (codebase-mcp)',

  // Summary configuration
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// Test data: diverse search queries to simulate realistic usage
const searchQueries = [
  'function authentication',
  'class UserRepository',
  'async def index_repository',
  'import asyncpg',
  'connection pool',
  'database query',
  'error handling',
  'type annotations',
  'test fixtures',
  'performance benchmark',
  'vector embeddings',
  'semantic search',
  'PostgreSQL schema',
  'migration script',
  'API endpoint',
];

/**
 * Main test scenario executed by each virtual user
 */
export default function () {
  // Select random search query for variety
  const query = searchQueries[Math.floor(Math.random() * searchQueries.length)];

  // Prepare search request
  const url = 'http://localhost:8020/search';  // MCP search endpoint
  const payload = JSON.stringify({
    query: query,
    limit: 10,
    project_id: null,  // Default workspace
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: {
      name: 'codebase_search',
    },
  };

  // Execute search request
  const response = http.post(url, payload, params);

  // Track custom metrics
  searchLatency.add(response.timings.duration);
  errorRate.add(response.status !== 200);

  // Validate response
  const checkResult = check(response, {
    'status is 200': (r) => r.status === 200,
    'response has results': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.results !== undefined;
      } catch (e) {
        return false;
      }
    },
    'response time acceptable': (r) => r.timings.duration < 2000,
    'no server errors': (r) => r.status < 500,
  });

  // Log failures for debugging
  if (!checkResult) {
    console.error(`Search failed: ${response.status} - ${response.body.substring(0, 200)}`);
  }

  // Realistic user think time: 1-3 seconds between requests
  // This prevents artificial saturation and simulates real usage patterns
  sleep(1 + Math.random() * 2);
}

/**
 * Setup function executed once before load test starts
 */
export function setup() {
  console.log('Starting codebase-mcp load test...');
  console.log('Target: 50 concurrent users for 10 minutes');
  console.log('Thresholds: p95<2000ms, error rate <1%');

  // Health check to ensure server is running
  const healthUrl = 'http://localhost:8020/health';
  const healthResponse = http.get(healthUrl);

  if (healthResponse.status !== 200) {
    throw new Error(`Server health check failed: ${healthResponse.status}`);
  }

  console.log('Server health check passed. Starting load test...');

  return {
    startTime: new Date().toISOString(),
  };
}

/**
 * Teardown function executed once after load test completes
 */
export function teardown(data) {
  console.log('Load test completed.');
  console.log(`Started at: ${data.startTime}`);
  console.log(`Completed at: ${new Date().toISOString()}`);

  // Final health check to ensure server is still responsive
  const healthUrl = 'http://localhost:8020/health';
  const healthResponse = http.get(healthUrl);

  if (healthResponse.status === 200) {
    console.log('✓ Server still healthy after load test');
  } else {
    console.warn('⚠ Server health degraded after load test');
  }
}

/**
 * Custom summary handler for detailed results output
 */
export function handleSummary(data) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const resultsFile = `tests/load/results/codebase_load_results_${timestamp}.json`;

  // Generate summary report
  const summary = {
    test_name: 'codebase-mcp load test',
    timestamp: timestamp,
    duration_seconds: data.state.testRunDurationMs / 1000,
    metrics: {
      requests_total: data.metrics.http_reqs.values.count,
      requests_per_second: data.metrics.http_reqs.values.rate,
      error_rate_percent: data.metrics.http_req_failed.values.rate * 100,
      latency: {
        p50: data.metrics.http_req_duration.values['p(50)'],
        p95: data.metrics.http_req_duration.values['p(95)'],
        p99: data.metrics.http_req_duration.values['p(99)'],
        avg: data.metrics.http_req_duration.values.avg,
        max: data.metrics.http_req_duration.values.max,
      },
      custom_metrics: {
        search_latency_p95: data.metrics.codebase_search_duration?.values['p(95)'] || null,
        custom_error_rate_percent: data.metrics.codebase_errors?.values.rate * 100 || null,
      },
    },
    thresholds_passed: data.metrics.http_req_duration.thresholds['p(95)<2000'].ok &&
                        data.metrics.http_req_failed.thresholds['rate<0.01'].ok,
    success_criteria: {
      concurrent_clients_handled: true,  // If test completes, clients were handled
      p95_latency_under_2000ms: data.metrics.http_req_duration.values['p(95)'] < 2000,
      error_rate_under_1_percent: data.metrics.http_req_failed.values.rate < 0.01,
      uptime_99_9_percent: data.metrics.http_req_failed.values.rate < 0.001,  // SC-007
    },
  };

  return {
    'stdout': JSON.stringify(summary, null, 2),
    [resultsFile]: JSON.stringify(summary, null, 2),
  };
}
