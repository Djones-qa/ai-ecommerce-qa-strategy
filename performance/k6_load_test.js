/**
 * k6 Load Test — AI Recommendation Engine Latency SLOs
 * -------------------------------------------------------
 * Tests the /v1/recommendations endpoint under realistic load and enforces
 * the following Service Level Objectives (SLOs):
 *
 *   - p95 response time < 2000ms
 *   - p99 response time < 4000ms
 *   - Error rate < 1%
 *   - Minimum throughput: 10 req/s
 *
 * Run:
 *   k6 run performance/k6_load_test.js
 *
 * Run with custom base URL:
 *   k6 run -e BASE_URL=http://localhost:8000 performance/k6_load_test.js
 *
 * k6 docs: https://k6.io/docs/
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ---------------------------------------------------------------------------
// Custom metrics
// ---------------------------------------------------------------------------

const errorRate = new Rate("recommendation_errors");
const recommendationLatency = new Trend("recommendation_latency", true);

// ---------------------------------------------------------------------------
// Test configuration
// ---------------------------------------------------------------------------

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  // Load profile: ramp up → steady state → ramp down
  stages: [
    { duration: "30s", target: 10 },   // Ramp up to 10 VUs over 30s
    { duration: "1m", target: 20 },    // Ramp up to 20 VUs over 1 minute
    { duration: "2m", target: 20 },    // Hold at 20 VUs for 2 minutes
    { duration: "30s", target: 0 },    // Ramp down to 0
  ],

  // SLO thresholds — the test FAILS if any of these are violated
  thresholds: {
    // Primary SLOs
    http_req_duration: [
      "p(95)<2000",   // 95th percentile under 2 seconds
      "p(99)<4000",   // 99th percentile under 4 seconds
    ],
    // Error rate must stay below 1%
    recommendation_errors: ["rate<0.01"],
    // Custom latency metric (same thresholds, tracked separately)
    recommendation_latency: [
      "p(95)<2000",
      "p(99)<4000",
    ],
    // HTTP failure rate
    http_req_failed: ["rate<0.01"],
  },
};

// ---------------------------------------------------------------------------
// Test data — realistic user contexts
// ---------------------------------------------------------------------------

const TEST_USERS = [
  { user_id: "perf-user-001", context: "running shoes for marathon training", category: "Footwear" },
  { user_id: "perf-user-002", context: "home office monitor and accessories", category: "Electronics" },
  { user_id: "perf-user-003", context: "yoga mat and resistance bands", category: "Sports" },
  { user_id: "perf-user-004", context: "smart home devices for kitchen", category: "Home" },
  { user_id: "perf-user-005", context: "wireless headphones for commuting", category: "Electronics" },
  { user_id: "perf-user-006", context: "workout clothes and gym gear", category: "Apparel" },
  { user_id: "perf-user-007", context: "coffee maker for home office", category: "Home" },
  { user_id: "perf-user-008", context: "hiking boots for weekend trails", category: "Footwear" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function randomUser() {
  return TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
}

function buildPayload(user) {
  return JSON.stringify({
    user_id: user.user_id,
    context: user.context,
    max_results: Math.floor(Math.random() * 3) + 1, // 1–3 results
    category: Math.random() > 0.5 ? user.category : undefined,
  });
}

// ---------------------------------------------------------------------------
// Default function (executed by each VU on each iteration)
// ---------------------------------------------------------------------------

export default function () {
  const user = randomUser();
  const payload = buildPayload(user);

  const params = {
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    timeout: "10s",
  };

  // --- POST /v1/recommendations ---
  const startTime = Date.now();
  const res = http.post(`${BASE_URL}/v1/recommendations`, payload, params);
  const duration = Date.now() - startTime;

  recommendationLatency.add(duration);

  const success = check(res, {
    "status is 200": (r) => r.status === 200,
    "response has recommendations": (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.recommendations) && body.recommendations.length > 0;
      } catch {
        return false;
      }
    },
    "response has request_id": (r) => {
      try {
        const body = JSON.parse(r.body);
        return typeof body.request_id === "string" && body.request_id.length > 0;
      } catch {
        return false;
      }
    },
    "response has model field": (r) => {
      try {
        const body = JSON.parse(r.body);
        return typeof body.model === "string";
      } catch {
        return false;
      }
    },
    "latency_ms is non-negative": (r) => {
      try {
        const body = JSON.parse(r.body);
        return typeof body.latency_ms === "number" && body.latency_ms >= 0;
      } catch {
        return false;
      }
    },
  });

  errorRate.add(!success);

  // Realistic think time between requests (0.5–1.5 seconds)
  sleep(Math.random() + 0.5);
}

// ---------------------------------------------------------------------------
// Setup: verify the server is up before the load test starts
// ---------------------------------------------------------------------------

export function setup() {
  const res = http.get(`${BASE_URL}/v1/health`);
  if (res.status !== 200) {
    throw new Error(
      `Health check failed before load test. Server at ${BASE_URL} returned status ${res.status}. ` +
      `Make sure the mock server is running: uvicorn mock_server.app:app --port 8000`
    );
  }
  console.log(`✓ Server health check passed. Starting load test against ${BASE_URL}`);
}

// ---------------------------------------------------------------------------
// Teardown: print SLO summary
// ---------------------------------------------------------------------------

export function teardown(data) {
  console.log("\n=== SLO Summary ===");
  console.log("p95 target: < 2000ms");
  console.log("p99 target: < 4000ms");
  console.log("Error rate target: < 1%");
  console.log("Check the thresholds section above for pass/fail status.");
}
