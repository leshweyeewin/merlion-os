/* MerlionOS — Home upfront-cost calculator pane.
 *
 * A purchase price + short buyer profile → POST /api/upfront-cost/estimate → the one-off cash/CPF
 * you need before you get the keys: Buyer's/Additional Stamp Duty, the down-payment split, and an
 * indicative EHG grant offset. Informational only; nothing is stored.
 * Mirrors the self-managing pane pattern of js/benefits.js. */
(function () {
    "use strict";

    const API = "/api/upfront-cost/estimate";

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

    const container = () => document.getElementById("hub-upfront-content");

    function load() {
        const el = container();
        if (!el) return;
        renderForm(el);
    }

    function renderForm(el) {
        el.innerHTML = `
        <div class="hub-card" style="margin-bottom:18px;">
            <h3><i class="fa-solid fa-house-circle-check"></i> Home Upfront-Cost Calculator</h3>
            <p style="font-size:13px; color:var(--text-muted); margin-bottom:14px;">
                Before you get the keys, how much cash and CPF do you actually need? Enter a price and a
                few details and we'll estimate the stamp duties, down-payment split, and any CPF Housing
                Grant. Nothing you enter is stored.</p>
            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px;">
                <label style="font-size:12px; color:var(--text-muted);">Purchase price (S$)<br>
                    <input id="uf-price" type="number" min="1" step="1000" placeholder="e.g. 600000" style="${INP} width:100%; box-sizing:border-box;"></label>
                <label style="font-size:12px; color:var(--text-muted);">Your residency<br>
                    ${sel("uf-residency", [["citizen", "Singapore Citizen"], ["pr", "Permanent Resident"], ["foreigner", "Foreigner"]], "100%")}</label>
                <label style="font-size:12px; color:var(--text-muted);">Residential properties you already own<br>
                    ${sel("uf-props", [["0", "None — this is my first"], ["1", "One"], ["2", "Two or more"]], "100%")}</label>
                <label style="font-size:12px; color:var(--text-muted);">Loan type<br>
                    ${sel("uf-loan", [["bank", "Bank loan"], ["hdb", "HDB loan (HFE)"]], "100%")}</label>
                <label style="font-size:12px; color:var(--text-muted);">Household (for grant)<br>
                    ${sel("uf-household", [["family", "Family / couple"], ["single", "Single"]], "100%")}</label>
                <label style="font-size:12px; color:var(--text-muted);">Gross monthly household income (S$)<br>
                    <input id="uf-income" type="number" min="0" step="100" placeholder="Optional — for grant" style="${INP} width:100%; box-sizing:border-box;"></label>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:18px; margin-top:14px; font-size:13px; color:var(--text-main);">
                <label style="cursor:pointer;"><input type="checkbox" id="uf-first"> First-timer household (no prior HDB flat / housing grant)</label>
            </div>
            <button id="uf-go" style="margin-top:16px; background:var(--primary); color:#fff; border:none;
                border-radius:6px; padding:9px 20px; font-weight:700; font-size:13px; cursor:pointer;">
                <i class="fa-solid fa-calculator"></i> Estimate my upfront cost</button>
            <span id="uf-msg" style="font-size:12px; margin-left:10px; color:var(--danger,#c0392b);"></span>
        </div>
        <div id="uf-results"></div>`;

        document.getElementById("uf-go").addEventListener("click", run);
    }

    function readInputs() {
        return {
            price: numOrBlank("uf-price"),
            residency: val("uf-residency"),
            properties_owned: parseInt(val("uf-props"), 10),
            loan_type: val("uf-loan"),
            household: val("uf-household"),
            monthly_income: numOrBlank("uf-income"),
            first_timer: document.getElementById("uf-first").checked,
        };
    }

    async function run() {
        const msg = document.getElementById("uf-msg");
        const out = document.getElementById("uf-results");
        msg.textContent = "";
        if (readInputs().price == null) { msg.textContent = "✗ Enter a purchase price first."; return; }
        out.innerHTML = `<div class="hub-card"><p style="margin:0; color:var(--text-muted);">Working out your upfront cost…</p></div>`;
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
        const linkFor = (key) => (d.links || {})[key] || "";
        const row = (l) => {
            const zero = !l.amount;
            const url = linkFor(l.key);
            const link = url
                ? ` <a href="${esc(url)}" target="_blank" rel="noopener" style="color:var(--primary); font-size:11px; font-weight:600; white-space:nowrap;"><i class="fa-solid fa-up-right-from-square"></i> official</a>`
                : "";
            return `<div style="padding:9px 0; border-top:1px solid var(--border);">
                <div style="display:flex; justify-content:space-between; align-items:baseline; gap:10px;">
                    <div style="font-weight:700; font-size:13px; color:var(--text-main);">${esc(l.label)}${link}</div>
                    <div style="font-weight:800; font-size:14px; color:${zero ? "var(--text-subtle)" : (l.key === "ehg" ? "var(--success,#1a7f3c)" : "var(--text-main)")};">${l.key === "ehg" && l.amount ? "− " : ""}${money(l.amount)}</div>
                </div>
                <div style="font-size:11.5px; color:var(--text-muted); margin-top:3px;">${esc(l.detail)}</div>
            </div>`;
        };

        const headline = `<div class="hub-card" style="margin-bottom:16px; border-left:4px solid var(--primary); background:rgba(52,120,246,.06);">
            <div style="font-size:12px; color:var(--text-muted);">Cash you need on hand at signing (min-cash down-payment + stamp duty)</div>
            <div style="font-size:24px; font-weight:800; color:var(--text-main); margin:2px 0 8px;">${money(d.cash_at_signing)}</div>
            <div style="display:flex; flex-wrap:wrap; gap:18px; font-size:12px; color:var(--text-muted);">
                <span>Total upfront (incl. CPF): <b style="color:var(--text-main);">${money(d.total_upfront)}</b></span>
                <span>Loan (${Math.round((d.loan_amount / d.price) * 100)}% LTV): <b style="color:var(--text-main);">${money(d.loan_amount)}</b></span>
                <span>CPF OA can cover: <b style="color:var(--text-main);">${money(d.cpf_needed)}</b> of the down-payment</span>
            </div>
            ${d.grant_eligible ? `<div style="font-size:12px; color:var(--success,#1a7f3c); font-weight:700; margin-top:8px;">
                With up to ${money(d.grant)} EHG into your CPF OA, your net upfront could fall to about ${money(d.net_after_grant)}.</div>` : ""}
        </div>`;

        const breakdown = `<div class="hub-card" style="margin-bottom:14px;">
            <div style="font-size:13px; font-weight:800; color:var(--text-main); margin-bottom:2px;">Breakdown for a ${money(d.price)} home</div>
            ${(d.lines || []).map(row).join("")}
        </div>`;

        const assumptions = (d.assumptions || []).length
            ? `<div class="hub-card" style="margin-bottom:12px; background:transparent;">
                <div style="font-size:12px; font-weight:700; color:var(--text-muted); margin-bottom:5px;">Assumptions</div>
                <ul style="margin:0; padding-left:18px; font-size:11.5px; color:var(--text-subtle);">
                    ${d.assumptions.map((a) => `<li style="margin-bottom:4px;">${esc(a)}</li>`).join("")}
                </ul></div>`
            : "";

        out.innerHTML = headline + breakdown + assumptions
            + `<div class="hub-card" style="background:transparent;">
                 <div style="font-size:11px; color:var(--text-subtle); font-style:italic;">${esc(d.disclaimer)}</div>
               </div>`;
    }

    window.MerlionUpfront = { load };
})();
