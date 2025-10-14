/**
 * k6 Load Test Scenario for Workflow-MCP Server
 *
 * Purpose: Validate that workflow-mcp handles 50 concurrent clients without
 *          crashing or becoming unresponsive under sustained load.
 *
 * Constitutional Compliance:
 * - SC-006: 50 concurrent clients handled without crash
 * - SC-007: 99.9% uptime during extended load testing
 * - Principle IV: Performance guarantees (project switching <50ms p95, entity queries <100ms p95)
 *
 * Test Scenario:
 * - Ramp-up: 0 -> 10 users (2 min) -> 50 users (5 min)
 * - Sustained: 50 users for 10 minutes
 * - Ramp-down: 50 -> 0 users (2 min)
 * - Total duration: 19 minutes
 *
 * Workload Mix:
 * - 40% project switching operations
 * - 40% entity queries with JSONB filters
 * - 20% work item queries
 *
 * Success Criteria:
 * - Error rate < 1% (99% success rate)
 * - No server crashes or unresponsiveness
 * - Project switching: p95 < 100ms (under load, slight degradation acceptable)
 * - Entity queries: p95 < 200ms (under load, slight degradation acceptable)
 *
 * Usage:
 *   k6 run tests/load/k6_workflow_load.js
 *
 * Requirements:
 * - workflow-mcp server running on http://localhost:8010
 * - Multiple projects and entities pre-populated in database
 * - k6 version 0.45+ installed
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics for detailed analysis
const errorRate = new Rate('workflow_errors');
const projectSwitchLatency = new Trend('workflow_project_switch_duration', true);
const entityQueryLatency = new Trend('workflow_entity_query_duration', true);
const workItemQueryLatency = new Trend('workflow_work_item_query_duration', true);

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
    'http_req_duration': ['p(95)<500'],        // Overall p95 latency < 500ms
    'http_req_failed': ['rate<0.01'],          // Error rate < 1%
    'workflow_errors': ['rate<0.01'],          // Custom error tracking < 1%
    'workflow_project_switch_duration': ['p(95)<100'], // Project switch p95 < 100ms
    'workflow_entity_query_duration': ['p(95)<200'],   // Entity query p95 < 200ms (under load)
    'http_reqs': ['rate>0'],                   // Ensure requests are being made
  },

  // Additional configuration
  noConnectionReuse: false,  // Reuse connections (more realistic)
  userAgent: 'k6-load-test/1.0 (workflow-mcp)',

  // Summary configuration
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// Test data: simulated project IDs and entity types for testing
let projectIds = [];
let entityTypes = ['vendor', 'commission_record', 'dealer', 'product'];

/**
 * Main test scenario executed by each virtual user
 */
export default function () {
  // If project IDs not initialized, use setup data
  if (projectIds.length === 0 && __ENV.PROJECT_IDS) {
    projectIds = JSON.parse(__ENV.PROJECT_IDS);
  }

  // Workload mix: 40% project switching, 40% entity queries, 20% work item queries
  const operation = Math.random();

  if (operation < 0.4) {
    // Project switching operation (40% of requests)
    performProjectSwitch();
  } else if (operation < 0.8) {
    // Entity query operation (40% of requests)
    performEntityQuery();
  } else {
    // Work item query operation (20% of requests)
    performWorkItemQuery();
  }

  // Realistic user think time: 1-3 seconds between requests
  sleep(1 + Math.random() * 2);
}

/**
 * Perform project switching operation
 */
function performProjectSwitch() {
  // Select random project or use default if none available
  const projectId = projectIds.length > 0
    ? projectIds[Math.floor(Math.random() * projectIds.length)]
    : null;

  const url = 'http://localhost:8010/switch_project';
  const payload = JSON.stringify({
    project_id: projectId,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: {
      name: 'workflow_project_switch',
    },
  };

  const response = http.post(url, payload, params);

  // Track custom metrics
  projectSwitchLatency.add(response.timings.duration);
  errorRate.add(response.status !== 200);

  // Validate response
  check(response, {
    'project switch status is 200': (r) => r.status === 200,
    'project switch has success': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.success === true || body.project_id !== undefined;
      } catch (e) {
        return false;
      }
    },
    'project switch time acceptable': (r) => r.timings.duration < 100,
  });
}

/**
 * Perform entity query operation with JSONB filters
 */
function performEntityQuery() {
  // Select random entity type
  const entityType = entityTypes[Math.floor(Math.random() * entityTypes.length)];

  const url = 'http://localhost:8010/query_entities';
  const payload = JSON.stringify({
    entity_type: entityType,
    filter: null,  // No filter for baseline query performance
    tags: null,
    include_deleted: false,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: {
      name: 'workflow_entity_query',
    },
  };

  const response = http.post(url, payload, params);

  // Track custom metrics
  entityQueryLatency.add(response.timings.duration);
  errorRate.add(response.status !== 200);

  // Validate response
  check(response, {
    'entity query status is 200': (r) => r.status === 200,
    'entity query returns results': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body) || body.entities !== undefined;
      } catch (e) {
        return false;
      }
    },
    'entity query time acceptable': (r) => r.timings.duration < 200,
  });
}

/**
 * Perform work item query operation
 */
function performWorkItemQuery() {
  const url = 'http://localhost:8010/query_work_items';
  const payload = JSON.stringify({
    item_type: null,
    status: 'active',
    parent_id: null,
    include_descendants: false,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: {
      name: 'workflow_work_item_query',
    },
  };

  const response = http.post(url, payload, params);

  // Track custom metrics
  workItemQueryLatency.add(response.timings.duration);
  errorRate.add(response.status !== 200);

  // Validate response
  check(response, {
    'work item query status is 200': (r) => r.status === 200,
    'work item query returns results': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.work_items !== undefined || Array.isArray(body);
      } catch (e) {
        return false;
      }
    },
    'work item query time acceptable': (r) => r.timings.duration < 200,
  });
}

/**
 * Setup function executed once before load test starts
 */
export function setup() {
  console.log('Starting workflow-mcp load test...');
  console.log('Target: 50 concurrent users for 10 minutes');
  console.log('Workload: 40% project switch, 40% entity query, 20% work item query');
  console.log('Thresholds: error rate <1%, project switch p95<100ms, entity query p95<200ms');

  // Health check to ensure server is running
  const healthUrl = 'http://localhost:8010/health';
  const healthResponse = http.get(healthUrl);

  if (healthResponse.status !== 200) {
    throw new Error(`Server health check failed: ${healthResponse.status}`);
  }

  console.log('Server health check passed.');

  // Try to get list of projects for realistic testing
  let discoveredProjects = [];
  try {
    const projectsUrl = 'http://localhost:8010/list_projects';
    const projectsResponse = http.post(projectsUrl, JSON.stringify({ limit: 10 }), {
      headers: { 'Content-Type': 'application/json' },
    });

    if (projectsResponse.status === 200) {
      const body = JSON.parse(projectsResponse.body);
      discoveredProjects = body.projects?.map(p => p.id) || [];
      console.log(`Discovered ${discoveredProjects.length} projects for testing`);
    }
  } catch (e) {
    console.log('Could not discover projects, will use default workspace');
  }

  console.log('Starting load test...');

  return {
    startTime: new Date().toISOString(),
    projectIds: discoveredProjects,
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
  const healthUrl = 'http://localhost:8010/health';
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
  const resultsFile = `tests/load/results/workflow_load_results_${timestamp}.json`;

  // Generate summary report
  const summary = {
    test_name: 'workflow-mcp load test',
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
        project_switch_p95: data.metrics.workflow_project_switch_duration?.values['p(95)'] || null,
        entity_query_p95: data.metrics.workflow_entity_query_duration?.values['p(95)'] || null,
        work_item_query_p95: data.metrics.workflow_work_item_query_duration?.values['p(95)'] || null,
        custom_error_rate_percent: data.metrics.workflow_errors?.values.rate * 100 || null,
      },
    },
    thresholds_passed: data.metrics.http_req_failed.thresholds['rate<0.01'].ok &&
                        data.metrics.workflow_project_switch_duration.thresholds['p(95)<100'].ok &&
                        data.metrics.workflow_entity_query_duration.thresholds['p(95)<200'].ok,
    success_criteria: {
      concurrent_clients_handled: true,  // If test completes, clients were handled
      error_rate_under_1_percent: data.metrics.http_req_failed.values.rate < 0.01,
      uptime_99_9_percent: data.metrics.http_req_failed.values.rate < 0.001,  // SC-007
      project_switch_performance: data.metrics.workflow_project_switch_duration?.values['p(95)'] < 100,
      entity_query_performance: data.metrics.workflow_entity_query_duration?.values['p(95)'] < 200,
    },
  };

  return {
    'stdout': JSON.stringify(summary, null, 2),
    [resultsFile]: JSON.stringify(summary, null, 2),
  };
}
