/* MerlionOS — Scam Checker pane.
 *
 * Paste a suspicious SMS / message / URL → POST /api/scam/check → render a heuristic verdict with
 * the specific red flags, safe-action advice, and official report links. Purely client-side state;
 * nothing is stored. Mirrors the self-managing pane pattern of js/alerts.js. */
(function () {
    "use strict";

    const API = "/api/scam/check";

    function esc(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
            ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }

    // Colour + icon per risk level, themed off the app's CSS variables.
    const LEVELS = {
        high:   { border: "var(--danger,#c0392b)",  bg: "rgba(192,57,43,.08)",  chip: "#c0392b" },
        medium: { border: "#e08a00",                 bg: "rgba(224,138,0,.08)",  chip: "#e08a00" },
        low:    { border: "#c9a800",                 bg: "rgba(201,168,0,.08)",  chip: "#a88b00" },
        none:   { border: "var(--success,#1a7f3c)",  bg: "rgba(26,127,60,.08)",  chip: "#1a7f3c" },
    };

    const EXAMPLES = [
        "Your DBS account has been suspended. Verify immediately at http://dbs-secure.xyz/login or it will be blocked within 24 hours.",
        "SingPost: your parcel is on hold due to unpaid customs fee. Pay here to release it: bit.ly/sg-parcel",
        "IRAS: you are eligible for a tax refund of $580. Confirm your details at https://iras.gov.sg",
    ];

    const container = () => document.getElementById("hub-scam-content");

    function load() {
        const el = container();
        if (!el) return;
        render(el);
    }

    function render(el) {
        el.innerHTML = `
        <div class="hub-card" style="margin-bottom:18px;">
            <h3><i class="fa-solid fa-shield-halved"></i> Scam Checker</h3>
            <p style="font-size:13px; color:var(--text-muted); margin-bottom:12px;">
                Got a suspicious SMS, WhatsApp, or email? Paste the message (or just the link) below and
                we'll flag the tell-tale signs of a scam — impersonated banks/agencies, dodgy links,
                pressure tactics. Nothing you paste is stored.</p>
            <textarea id="scam-input" rows="5" placeholder="Paste the suspicious message or URL here…"
                style="width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid var(--border);
                border-radius:8px; background:var(--bg-panel); color:var(--text-main); font-size:13px;
                font-family:inherit; resize:vertical;"></textarea>
            <div style="display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin-top:10px;">
                <button id="scam-check-btn" style="background:var(--primary); color:#fff; border:none;
                    border-radius:6px; padding:8px 18px; font-weight:700; font-size:13px; cursor:pointer;">
                    <i class="fa-solid fa-magnifying-glass"></i> Check message</button>
                <button id="scam-clear-btn" style="background:none; border:1px solid var(--border);
                    color:var(--text-muted); border-radius:6px; padding:8px 14px; font-size:12px; cursor:pointer;">Clear</button>
                <span style="font-size:11px; color:var(--text-subtle);">or try an example:</span>
                ${EXAMPLES.map((_, i) => `<button class="scam-eg" data-eg="${i}" style="background:none;
                    border:1px dashed var(--border); color:var(--text-muted); border-radius:12px;
                    padding:3px 10px; font-size:11px; cursor:pointer;">Example ${i + 1}</button>`).join("")}
            </div>
        </div>
        <div id="scam-result"></div>`;

        document.getElementById("scam-check-btn").addEventListener("click", runCheck);
        document.getElementById("scam-clear-btn").addEventListener("click", () => {
            document.getElementById("scam-input").value = "";
            document.getElementById("scam-result").innerHTML = "";
        });
        el.querySelectorAll(".scam-eg").forEach(b =>
            b.addEventListener("click", () => {
                document.getElementById("scam-input").value = EXAMPLES[+b.getAttribute("data-eg")];
            }));
        // Ctrl/Cmd+Enter to check.
        document.getElementById("scam-input").addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") runCheck();
        });
    }

    async function runCheck() {
        const input = document.getElementById("scam-input");
        const out = document.getElementById("scam-result");
        const text = (input.value || "").trim();
        if (!text) { out.innerHTML = ""; return; }
        out.innerHTML = `<div class="hub-card"><p style="margin:0; color:var(--text-muted);">Checking…</p></div>`;
        try {
            const res = await fetch(API, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text }),
            });
            if (!res.ok) {
                let detail = res.statusText;
                try { detail = (await res.json()).detail || detail; } catch (e) { /* ignore */ }
                throw new Error(detail);
            }
            renderResult(out, await res.json());
        } catch (err) {
            out.innerHTML = `<div class="hub-card"><p style="margin:0; color:var(--danger,#c0392b);">
                Couldn't check that: ${esc(err.message)}</p></div>`;
        }
    }

    function renderResult(out, r) {
        const lvl = LEVELS[r.level] || LEVELS.none;
        const reasons = (r.reasons || []).length
            ? `<ul style="margin:8px 0 0; padding-left:18px; font-size:13px; color:var(--text-main);">
                ${r.reasons.map(x => `<li style="margin-bottom:4px;">${esc(x)}</li>`).join("")}</ul>`
            : `<p style="font-size:13px; color:var(--text-muted); margin:8px 0 0;">No specific red flags detected in the text.</p>`;

        const urls = (r.urls || []).length
            ? `<div style="font-size:12px; color:var(--text-muted); margin-top:10px;">
                Links found: ${r.urls.map(u => `<code style="background:var(--bg-panel); padding:1px 5px; border-radius:4px;">${esc(u)}</code>`).join(" ")}</div>`
            : "";

        const advice = `<ul style="margin:8px 0 0; padding-left:18px; font-size:12px; color:var(--text-muted);">
            ${(r.advice || []).map(a => `<li style="margin-bottom:3px;">${esc(a)}</li>`).join("")}</ul>`;

        const links = (r.report_links || []).map(l =>
            `<a href="${esc(l.url)}" target="_blank" rel="noopener" style="color:var(--primary); font-size:12px; font-weight:600; margin-right:14px;">
                <i class="fa-solid fa-up-right-from-square"></i> ${esc(l.label)}</a>`).join("");

        out.innerHTML = `
        <div class="hub-card" style="border-left:4px solid ${lvl.border}; background:${lvl.bg};">
            <div style="font-size:16px; font-weight:800; color:${lvl.chip};">${esc(r.label)}</div>
            <div style="margin-top:4px; font-size:11px; color:var(--text-subtle);">Risk score: ${esc(String(r.score))}</div>
            ${reasons}
            ${urls}
            <div style="margin-top:14px; font-weight:700; font-size:12px; color:var(--text-main);">What to do:</div>
            ${advice}
            <div style="margin-top:12px;">${links}</div>
            <div style="margin-top:12px; font-size:11px; color:var(--text-subtle); font-style:italic;">${esc(r.disclaimer || "")}</div>
        </div>`;
    }

    window.MerlionScam = { load };
})();
