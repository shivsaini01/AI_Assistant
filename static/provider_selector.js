(function (root, factory) {
    const api = factory();
    if (typeof module === "object" && module.exports) module.exports = api;
    if (root) root.JarvisProviderSelector = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
    "use strict";

    const PROVIDERS = ["groq", "deepseek", "gemini", "local"];

    function normalizeProvider(value) {
        const normalized = typeof value === "string" ? value.trim().toLowerCase() : "";
        if (normalized === "online") return "groq";
        if (normalized === "offline") return "local";
        return PROVIDERS.includes(normalized) ? normalized : "groq";
    }

    function isProvider(value) {
        return typeof value === "string" && PROVIDERS.includes(value);
    }

    function shouldApplyProviderResponse(currentProvider, submittedProvider) {
        return currentProvider === submittedProvider;
    }

    return { normalizeProvider, isProvider, shouldApplyProviderResponse };
});
