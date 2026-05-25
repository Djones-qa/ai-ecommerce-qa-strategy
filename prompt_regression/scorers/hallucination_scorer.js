/**
 * Custom PromptFoo Hallucination Scorer
 * ---------------------------------------
 * Checks whether the LLM's recommended products exist in the known product
 * catalog. Returns a score of 1.0 (pass) if all products are real, or 0.0
 * (fail) if any hallucinated product is detected.
 *
 * Used in promptfooconfig.yaml as a custom scorer assertion.
 */

const fs = require("fs");
const path = require("path");

// Load the product catalog
const catalogPath = path.join(
  __dirname,
  "../../tests/hallucination/product_catalog.json"
);
const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf-8"));
const knownProductIds = new Set(catalog.products.map((p) => p.product_id));
const priceMap = Object.fromEntries(
  catalog.products.map((p) => [p.product_id, p.price])
);

/**
 * @param {object} params
 * @param {string} params.output - The LLM's raw output string
 * @param {object} params.context - Test context (vars, prompt, etc.)
 * @returns {{ pass: boolean, score: number, reason: string }}
 */
module.exports = async function hallucinationScorer({ output, context }) {
  let recommendations;

  // Try to parse the output as JSON
  try {
    // Handle both raw arrays and objects with a recommendations key
    const parsed = JSON.parse(output);
    recommendations = Array.isArray(parsed)
      ? parsed
      : parsed.recommendations || [];
  } catch (err) {
    return {
      pass: false,
      score: 0,
      reason: `Failed to parse LLM output as JSON: ${err.message}. Output: ${output.slice(0, 200)}`,
    };
  }

  if (!Array.isArray(recommendations) || recommendations.length === 0) {
    return {
      pass: false,
      score: 0,
      reason: "No recommendations found in LLM output.",
    };
  }

  const violations = [];

  for (const rec of recommendations) {
    const pid = rec.product_id;

    // Check 1: product_id must exist in catalog
    if (!knownProductIds.has(pid)) {
      violations.push(`Unknown product_id: '${pid}' not found in catalog`);
      continue;
    }

    // Check 2: price must match catalog (within $0.01 tolerance)
    const catalogPrice = priceMap[pid];
    const responsePrice = rec.price;
    if (Math.abs(responsePrice - catalogPrice) > 0.01) {
      violations.push(
        `Price mismatch for ${pid}: catalog=$${catalogPrice}, response=$${responsePrice}`
      );
    }

    // Check 3: confidence_score must be between 0 and 1
    if (rec.confidence_score < 0 || rec.confidence_score > 1) {
      violations.push(
        `Invalid confidence_score for ${pid}: ${rec.confidence_score} (must be 0.0–1.0)`
      );
    }
  }

  if (violations.length > 0) {
    return {
      pass: false,
      score: 0,
      reason: `Hallucination detected:\n${violations.map((v) => `  - ${v}`).join("\n")}`,
    };
  }

  return {
    pass: true,
    score: 1,
    reason: `All ${recommendations.length} recommended product(s) verified against catalog.`,
  };
};
