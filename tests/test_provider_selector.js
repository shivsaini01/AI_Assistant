"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");
const { normalizeProvider, shouldApplyProviderResponse } = require("../static/provider_selector.js");

test("migrates legacy preferences and validates provider values", () => {
    assert.equal(normalizeProvider("online"), "groq");
    assert.equal(normalizeProvider("offline"), "local");
    assert.equal(normalizeProvider("gemini"), "gemini");
    assert.equal(normalizeProvider("unexpected"), "groq");
});

test("does not apply a stale request response after provider selection changes", () => {
    assert.equal(shouldApplyProviderResponse("deepseek", "groq"), false);
    assert.equal(shouldApplyProviderResponse("groq", "groq"), true);
});
