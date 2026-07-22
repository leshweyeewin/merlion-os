// utils.js — Shared sanitizers used across every MerlionOS front-end module.
// escapeHTML / safeURL guard every innerHTML/attribute interpolation against XSS.

// Sanitize any string before inserting into innerHTML to prevent XSS
function escapeHTML(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Sanitizes and escapes URLs to prevent XSS or attribute breakout
function safeURL(url) {
    const clean = String(url).trim();
    const lower = clean.toLowerCase();
    if (lower.startsWith("javascript:") || lower.startsWith("data:") || lower.startsWith("vbscript:")) {
        return "#";
    }
    // Escape quotes to prevent HTML attribute breakout
    return clean.replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

