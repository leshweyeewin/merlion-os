/* MerlionOS — Benefits Finder pane.
 *
 * A short profile form → POST /api/eligibility/check → the government schemes you're likely
 * eligible for, with indicative amounts and official links. Informational only; nothing is stored.
 * Mirrors the self-managing pane pattern of js/scam.js. */
(function () {
    "use strict";

    const API = "/api/eligibility/check";

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

    // STATUS colours/icons — labels come from HUB_I18N so they translate with the form.
    const STATUS = {
        eligible: { color: "var(--success,#1a7f3c)", bg: "rgba(26,127,60,.07)", icon: "✅" },
        maybe:    { color: "#e08a00",               bg: "rgba(224,138,0,.07)",  icon: "❓" },
        not:      { color: "var(--text-subtle)",    bg: "transparent",          icon: "—" },
    };

    const container = () => document.getElementById("hub-benefits-content");

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
        const resultsEl = el.querySelector("#bf-results");
        const savedResults = resultsEl ? resultsEl.innerHTML : null;
        renderForm(el);
        if (savedResults !== null) {
            const newResults = el.querySelector("#bf-results");
            if (newResults) newResults.innerHTML = savedResults;
        }
    }

    function renderForm(el) {
        el.innerHTML = `
        <div class="hub-card" style="margin-bottom:18px;">
            <h3><i class="fa-solid fa-hand-holding-dollar"></i> ${esc(T("bf-title"))}</h3>
            <p style="font-size:13px; color:var(--text-muted); margin-bottom:14px;">
                ${esc(T("bf-desc"))}</p>
            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px;">
                <label style="font-size:12px; color:var(--text-muted);">${esc(T("bf-label-citizenship"))}<br>
                    ${sel("bf-citizenship", [["citizen", T("mp-opt-citizen")], ["pr", T("mp-opt-pr")], ["foreigner", T("mp-opt-foreigner")]], "100%")}</label>
                <label style="font-size:12px; color:var(--text-muted);">${esc(T("bf-label-age"))}<br>
                    <input id="bf-age" type="number" min="0" max="120" placeholder="e.g. 35" style="${INP} width:100%; box-sizing:border-box;"></label>
                <label style="font-size:12px; color:var(--text-muted);">${esc(T("bf-label-income"))}<br>
                    <input id="bf-income" type="number" min="0" step="100" placeholder="e.g. 2500" style="${INP} width:100%; box-sizing:border-box;"></label>
                <label style="font-size:12px; color:var(--text-muted);">${esc(T("bf-label-av"))}<br>
                    <input id="bf-av" type="number" min="0" step="1000" placeholder="Leave blank if unsure" style="${INP} width:100%; box-sizing:border-box;"></label>
                <label style="font-size:12px; color:var(--text-muted);">${esc(T("bf-label-props"))}<br>
                    ${sel("bf-props", [["0", T("mp-opt-none")], ["1", T("mp-opt-one")], ["2", T("mp-opt-two-plus")]], "100%")}</label>
                <label style="font-size:12px; color:var(--text-muted);">${esc(T("bf-label-marital"))}<br>
                    ${sel("bf-marital", [["married", T("bf-opt-married")], ["single", T("uf-opt-single")]], "100%")}</label>
                <label style="font-size:12px; color:var(--text-muted);">${esc(T("bf-label-employment"))}<br>
                    ${sel("bf-employment", [
                        ["employed",     T("bf-opt-employed")],
                        ["self_employed", T("bf-opt-self-emp")],
                        ["unemployed",   T("bf-opt-not-working")],
                        ["retired",      T("bf-opt-retired")],
                        ["student",      T("bf-opt-student")]
                    ], "100%")}</label>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:18px; margin-top:14px; font-size:13px; color:var(--text-main);">
                <label style="cursor:pointer;"><input type="checkbox" id="bf-child"> ${esc(T("bf-label-child"))}</label>
                <label style="cursor:pointer;"><input type="checkbox" id="bf-hdb"> ${esc(T("bf-label-hdb"))}</label>
            </div>
            <button id="bf-go" style="margin-top:16px; background:var(--primary); color:#fff; border:none;
                border-radius:6px; padding:9px 20px; font-weight:700; font-size:13px; cursor:pointer;">
                <i class="fa-solid fa-magnifying-glass-dollar"></i> ${esc(T("bf-btn-go"))}</button>
            <span id="bf-msg" style="font-size:12px; margin-left:10px; color:var(--danger,#c0392b);"></span>
        </div>
        <div id="bf-results"></div>`;

        document.getElementById("bf-go").addEventListener("click", run);
    }

    function readProfile() {
        return {
            citizenship: val("bf-citizenship"),
            age: numOrBlank("bf-age"),
            monthly_income: numOrBlank("bf-income"),
            home_av: numOrBlank("bf-av"),
            properties_owned: parseInt(val("bf-props"), 10),
            marital_status: val("bf-marital"),
            employment: val("bf-employment"),
            new_child: document.getElementById("bf-child").checked,
            buying_hdb: document.getElementById("bf-hdb").checked,
        };
    }

    async function run() {
        const msg = document.getElementById("bf-msg");
        const out = document.getElementById("bf-results");
        msg.textContent = "";
        out.innerHTML = `<div class="hub-card"><p style="margin:0; color:var(--text-muted);">${esc(T("bf-loading"))}</p></div>`;
        try {
            const res = await fetch(API, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ profile: readProfile() }),
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

    function money(n) { return "$" + Number(n || 0).toLocaleString("en-SG"); }

    function renderResults(out, data) {
        const eligible = (data.results || []).filter(r => r.status === "eligible");
        const headline = eligible.length
            ? `<div class="hub-card" style="margin-bottom:16px; border-left:4px solid var(--success,#1a7f3c); background:rgba(26,127,60,.07);">
                <div style="font-size:15px; font-weight:800; color:var(--text-main);">
                    You may be eligible for ${eligible.length} scheme${eligible.length > 1 ? "s" : ""}, worth roughly ${money(data.headline_total)}.</div>
                <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">
                    Approx. ${money(data.yearly_total)} recurring per year + ${money(data.one_time_total)} one-time. Indicative — verify each on its official site.</div>
               </div>`
            : `<div class="hub-card" style="margin-bottom:16px;">
                <div style="font-size:14px; font-weight:700; color:var(--text-main);">No clear matches from these answers.</div>
                <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">Many schemes are for Singapore citizens or specific situations. See the notes below, and check LifeSG for the full picture.</div>
               </div>`;

        const card = (r) => {
            const s = STATUS[r.status] || STATUS.not;
            // Status label is sourced from HUB_I18N so it reflects the active language.
            const statusLabel = T("bf-status-" + r.status) !== ("bf-status-" + r.status)
                ? T("bf-status-" + r.status) : r.status;
            return `<div class="hub-card" style="margin-bottom:10px; background:${s.bg};">
                <div style="display:flex; justify-content:space-between; align-items:baseline; gap:10px; flex-wrap:wrap;">
                    <div style="font-weight:700; font-size:14px; color:var(--text-main);">${s.icon} ${esc(r.name)}</div>
                    <div style="font-weight:800; font-size:14px; color:${s.color};">${esc(r.amount)}</div>
                </div>
                <div style="font-size:11px; font-weight:700; color:${s.color}; margin-top:2px;">${esc(statusLabel)}</div>
                <div style="font-size:12px; color:var(--text-muted); margin-top:5px;">${esc(r.why)}</div>
                ${r.note ? `<div style="font-size:11px; color:var(--text-subtle); margin-top:3px;">${esc(r.note)}</div>` : ""}
                <a href="${esc(r.apply_url)}" target="_blank" rel="noopener" style="display:inline-block; margin-top:7px; color:var(--primary); font-size:12px; font-weight:600;">
                    <i class="fa-solid fa-up-right-from-square"></i> Official site</a>
            </div>`;
        };

        const eligibleAndMaybe = (data.results || []).filter(r => r.status !== "not");
        const notEligible = (data.results || []).filter(r => r.status === "not");

        const notSection = notEligible.length
            ? `<details style="margin-top:6px;"><summary style="cursor:pointer; font-size:13px; color:var(--text-muted); padding:6px 0;">
                    Not eligible (${notEligible.length}) — tap to see why</summary>
                ${notEligible.map(card).join("")}</details>`
            : "";

        out.innerHTML = headline
            + eligibleAndMaybe.map(card).join("")
            + notSection
            + `<div class="hub-card" style="margin-top:12px; background:transparent;">
                 <div style="font-size:11px; color:var(--text-subtle); font-style:italic;">${esc(data.disclaimer)}</div>
               </div>`;
    }

    window.MerlionBenefits = { load, reload };
})();
