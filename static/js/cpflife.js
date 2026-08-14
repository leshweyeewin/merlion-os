/* MerlionOS — CPF LIFE payout projector pane.
 *
 * Expected Retirement Account savings at 55 (+ optional payout-start age) → POST /api/cpf-life/estimate
 * → the Retirement Sum tier reached and an indicative monthly CPF LIFE payout range, with the gap to
 * the next tier. Informational projection only; nothing is stored.
 * Mirrors the self-managing pane pattern of js/upfront.js. */
(function () {
    "use strict";

    const API = "/api/cpf-life/estimate";

    // i18n helper — falls back to the key string if translations haven't loaded yet.
    const T = (k) => (window.hubT ? window.hubT(k) : k);

    function esc(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
            ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }

    const INP = "padding:6px 9px; border:1px solid var(--border); border-radius:6px; background:var(--bg-panel); color:var(--text-main); font-size:13px;";
    const val = (id) => (document.getElementById(id) || {}).value || "";
    const numOrBlank = (id) => { const v = val(id).trim(); return v === "" ? null : parseInt(v, 10); };

    function sel(id, opts, width) {
        return `<select id="${id}" style="${INP} width:${width || "auto"};">` +
            opts.map(([v, label]) => `<option value="${esc(v)}">${esc(label)}</option>`).join("") + "</select>";
    }

    function money(n) { return "$" + Number(n || 0).toLocaleString("en-SG"); }
    const range = (lo, hi) => `${money(lo)}–${money(hi)}`;

    const container = () => document.getElementById("hub-cpflife-content");

    function load() {
        const el = container();
        if (!el) return;
        renderForm(el);
    }

    // reload() re-renders the form chrome in the current language without clearing the results div.
    // Called by hub.js on merlion:languagechange.
    function reload() {
        const el = container();
        if (!el) return;
        const resultsEl = el.querySelector("#cl-results");
        const savedResults = resultsEl ? resultsEl.innerHTML : null;
        renderForm(el);
        if (savedResults !== null) {
            const newResults = el.querySelector("#cl-results");
            if (newResults) newResults.innerHTML = savedResults;
        }
    }

    function renderForm(el) {
        el.innerHTML = `
        <div class="hub-card" style="margin-bottom:18px;">
            <h3><i class="fa-solid fa-piggy-bank"></i> ${esc(T("cl-title"))}</h3>
            <p style="font-size:13px; color:var(--text-muted); margin-bottom:14px;">
                ${esc(T("cl-desc"))}</p>
            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px;">
                <label style="font-size:12px; color:var(--text-muted);">${esc(T("cl-label-ra"))}<br>
                    <input id="cl-ra" type="number" min="0" step="1000" placeholder="e.g. 220400" style="${INP} width:100%; box-sizing:border-box;"></label>
                <label style="font-size:12px; color:var(--text-muted);">${esc(T("cl-label-age"))}<br>
                    ${sel("cl-age", [
                        ["65", T("cl-opt-65")], ["66", T("cl-opt-66")], ["67", T("cl-opt-67")],
                        ["68", T("cl-opt-68")], ["69", T("cl-opt-69")], ["70", T("cl-opt-70")]
                    ], "100%")}</label>
                <label style="font-size:12px; color:var(--text-muted);">${esc(T("cl-label-cur"))}<br>
                    <input id="cl-cur" type="number" min="0" max="120" placeholder="e.g. 40" style="${INP} width:100%; box-sizing:border-box;"></label>
            </div>
            <button id="cl-go" style="margin-top:16px; background:var(--primary); color:#fff; border:none;
                border-radius:6px; padding:9px 20px; font-weight:700; font-size:13px; cursor:pointer;">
                <i class="fa-solid fa-chart-line"></i> ${esc(T("cl-btn-go"))}</button>
            <span id="cl-msg" style="font-size:12px; margin-left:10px; color:var(--danger,#c0392b);"></span>
        </div>
        <div id="cl-results"></div>`;

        document.getElementById("cl-go").addEventListener("click", run);
    }

    function readInputs() {
        return {
            ra_savings: numOrBlank("cl-ra"),
            payout_age: parseInt(val("cl-age"), 10),
            current_age: numOrBlank("cl-cur"),
        };
    }

    async function run() {
        const msg = document.getElementById("cl-msg");
        const out = document.getElementById("cl-results");
        msg.textContent = "";
        if (readInputs().ra_savings == null) { msg.textContent = T("cl-err-ra"); return; }
        out.innerHTML = `<div class="hub-card"><p style="margin:0; color:var(--text-muted);">${esc(T("cl-loading"))}</p></div>`;
        try {
            const res = await fetch(API, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ inputs: readInputs() }),
            });
            if (!res.ok) {
                let detail = res.statusText;
                try { detail = (await res.json()).detail || detail; } catch (e) { /* ignore */ }
                throw new Error(detail);
            }
            renderResults(out, await res.json());
        } catch (err) {
            out.innerHTML = "";
            msg.textContent = "✗ " + err.message;
        }
    }

    function renderResults(out, d) {
        const below = d.tier === "below_brs";
        const headline = `<div class="hub-card" style="margin-bottom:16px; border-left:4px solid var(--primary); background:rgba(52,120,246,.06);">
            <div style="font-size:12px; color:var(--text-muted);">Indicative CPF LIFE payout from age ${d.payout_age} (Standard Plan)</div>
            <div style="font-size:24px; font-weight:800; color:var(--text-main); margin:2px 0 6px;">${range(d.payout_low, d.payout_high)}<span style="font-size:13px; font-weight:600; color:var(--text-muted);"> / month</span></div>
            <div style="font-size:12px; color:var(--text-muted);">Your ${money(d.ra_savings)} ${below ? "is below the Basic Retirement Sum" : "reaches the <b style=\"color:var(--text-main);\">" + esc(d.tier_name) + "</b>"}.</div>
            ${d.next_tier ? `<div style="font-size:12px; color:var(--success,#1a7f3c); font-weight:600; margin-top:8px;">
                ${money(d.next_tier.gap)} more would reach the ${esc(d.next_tier.name.split(" (")[0])} — raising the estimate to ~${range(d.next_tier.payout_low, d.next_tier.payout_high)}/month (about +${money(d.next_tier.adds_low)}–${money(d.next_tier.adds_high)}).</div>` : `<div style="font-size:12px; color:var(--success,#1a7f3c); font-weight:600; margin-top:8px;">You're at the highest tier (Enhanced Retirement Sum).</div>`}
        </div>`;

        const tierRow = (t) => {
            const hit = t.key === d.tier;
            return `<div style="padding:9px 0; border-top:1px solid var(--border); ${hit ? "" : "opacity:.72;"}">
                <div style="display:flex; justify-content:space-between; align-items:baseline; gap:10px;">
                    <div style="font-weight:700; font-size:13px; color:var(--text-main);">${hit ? "➤ " : ""}${esc(t.name)}</div>
                    <div style="font-weight:800; font-size:13px; color:var(--text-main);">${money(t.sum)}</div>
                </div>
                <div style="font-size:11.5px; color:var(--text-muted); margin-top:3px;">Indicative payout ~${range(t.payout_low, t.payout_high)}/month from age ${d.payout_age}.</div>
            </div>`;
        };

        const tiers = `<div class="hub-card" style="margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:baseline; gap:10px; flex-wrap:wrap; margin-bottom:2px;">
                <div style="font-size:13px; font-weight:800; color:var(--text-main);">${esc(d.rules_year)} Retirement Sums (turning 55)</div>
                <a href="${esc(d.links.estimator)}" target="_blank" rel="noopener" style="color:var(--primary); font-size:12px; font-weight:600;"><i class="fa-solid fa-up-right-from-square"></i> Official CPF LIFE Estimator</a>
            </div>
            ${(d.sums || []).map(tierRow).join("")}
        </div>`;

        const notes = (d.notes || []).length
            ? `<div class="hub-card" style="margin-bottom:12px; background:transparent;">
                <ul style="margin:0; padding-left:18px; font-size:11.5px; color:var(--text-subtle);">
                    ${d.notes.map((n) => `<li style="margin-bottom:4px;">${esc(n)}</li>`).join("")}
                </ul></div>`
            : "";

        out.innerHTML = headline + tiers + notes
            + `<div class="hub-card" style="background:transparent;">
                 <div style="font-size:11px; color:var(--text-subtle); font-style:italic;">${esc(d.disclaimer)}</div>
               </div>`;
    }

    window.MerlionCpfLife = { load, reload };
})();
