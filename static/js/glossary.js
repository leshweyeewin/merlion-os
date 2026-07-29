// glossary.js — Plain-English glossary for SG Hub
// -----------------------------------------------------------------------------
// Extracted from hub.js into its own module for maintainability. It scans the SG Hub pane for
// known civic acronyms and gives each a dashed underline with a one-sentence explanation on
// hover/tap — because gov dashboards are "peppered with acronyms" that otherwise force users to
// open a separate tab to decode their own statements.
//
// Self-contained: it owns its tooltip element (so it never touches hub.js's chart tooltip) and
// boots itself on DOMContentLoaded. Depends only on the global escapeHTML() from utils.js.

(function () {
    "use strict";

    const SG_GLOSSARY = {
        "CPF": "Central Provident Fund — Singapore's mandatory savings scheme for retirement, housing and healthcare.",
        "OA": "Ordinary Account — the CPF account usable for housing, insurance, investment and education.",
        "SA": "Special Account — the CPF account reserved for retirement, earning higher interest (~4% p.a.).",
        "MediSave": "The CPF account for hospital bills, approved outpatient treatments and medical insurance premiums.",
        "RSTU": "Retirement Sum Topping-Up scheme — cash top-ups to CPF retirement savings, with tax relief of up to S$8,000/yr (self) + S$8,000/yr (family).",
        "SRS": "Supplementary Retirement Scheme — a voluntary account giving dollar-for-dollar tax relief; only 50% of withdrawals are taxable after retirement age.",
        "COE": "Certificate of Entitlement — the quota licence won at auction that lets you register and use a vehicle in Singapore for 10 years.",
        "PSI": "Pollutant Standards Index — Singapore's air-quality measure: 0–50 good, 51–100 moderate, above 100 unhealthy.",
        "PM2.5": "Fine airborne particles under 2.5 microns — the main pollutant during haze episodes.",
        "BTO": "Build-To-Order — new HDB flats balloted and sold before construction, typically completed in 3–5 years.",
        "EHG": "Enhanced CPF Housing Grant — an income-tiered grant of up to S$120,000 for eligible first-time flat buyers.",
        "HDB": "Housing & Development Board — Singapore's public housing authority.",
        "IRAS": "Inland Revenue Authority of Singapore — the national tax collector.",
        "YA": "Year of Assessment — the tax year; YA 2026 assesses income earned during 2025.",
        "GST": "Goods and Services Tax — Singapore's 9% consumption tax.",
        "ECI": "Estimated Chargeable Income — a company's estimate of taxable profit, filed within 3 months of its financial year end.",
        "CRS": "Common Reporting Standard — the international framework for exchanging financial account data between tax authorities.",
        "SSOC": "Singapore Standard Occupational Classification — the official taxonomy of job titles used in national wage statistics.",
        "MOM": "Ministry of Manpower — regulates employment, work passes and workplace safety.",
        "LTA": "Land Transport Authority — plans and regulates Singapore's roads, rail and vehicle ownership.",
        "NEA": "National Environment Agency — manages environmental health, weather and pollution monitoring.",
        "SSB": "Singapore Savings Bonds — low-risk government bonds redeemable in any month without penalty.",
        "CDC": "Community Development Council — district-level bodies that distribute local assistance like CDC vouchers.",
        "ICA": "Immigration & Checkpoints Authority — handles passports, NRICs, PRs and border checkpoints.",
        "IR8A": "The employer-issued form reporting your yearly employment income for tax filing.",
        "UV Index": "Measure of sunburn-causing ultraviolet radiation: 0–2 low, 6–7 high, 11+ extreme (NEA scale).",
        "CAGR": "Compound Annual Growth Rate — the steady yearly growth rate that would take a figure from its starting value to its ending value over the given number of years.",
        "MOP": "Minimum Occupation Period — the years (usually five) you must live in an HDB flat before you can sell it or rent it out whole.",
        "ABSD": "Additional Buyer's Stamp Duty — an extra property tax that rises with the number of homes you own and for PRs and foreigners.",
        "HFE": "HDB Flat Eligibility letter — the single upfront check of your eligibility, grants and loan before you buy a flat.",
        "accrued interest": "The CPF interest you must refund (on top of the principal) to your own CPF account when you sell a property bought with CPF savings.",
    };

    const GLOSS_RE = new RegExp(
        "(?<![\\w-])("
        + Object.keys(SG_GLOSSARY).sort((a, b) => b.length - a.length)
            .map(t => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")
        + ")(?![\\w-])"
    );

    // ── Self-owned tooltip (independent of hub.js's chart tooltip) ────────────
    let tipEl = null;
    function tooltip() {
        if (!tipEl) {
            tipEl = document.createElement("div");
            tipEl.style.cssText = "position:fixed; z-index:9999; pointer-events:none; background:var(--bg-panel); border:1px solid var(--border); border-radius:6px; padding:6px 10px; font-size:11.5px; color:var(--text-main); box-shadow:0 2px 10px rgba(0,0,0,0.14); display:none; max-width:280px; line-height:1.5;";
            document.body.appendChild(tipEl);
        }
        return tipEl;
    }
    function showTip(html, clientX, clientY) {
        const t = tooltip();
        t.innerHTML = html;
        t.style.display = "block";
        const pad = 12;
        const r = t.getBoundingClientRect();
        let x = clientX + pad, y = clientY + pad;
        if (x + r.width > window.innerWidth - 8) x = clientX - r.width - pad;
        if (y + r.height > window.innerHeight - 8) y = clientY - r.height - pad;
        x = Math.max(8, Math.min(x, window.innerWidth - r.width - 8));
        y = Math.max(8, Math.min(y, window.innerHeight - r.height - 8));
        t.style.left = x + "px";
        t.style.top = y + "px";
    }
    function hideTip() { if (tipEl) tipEl.style.display = "none"; }

    // escapeHTML comes from utils.js (loaded first); fall back to a local escaper just in case.
    const esc = (typeof escapeHTML === "function")
        ? escapeHTML
        : (s) => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

    let glossAnnotating = false;
    function annotateGlossary(root) {
        if (!root || glossAnnotating) return;
        glossAnnotating = true;
        try {
            const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
                acceptNode(n) {
                    if (!n.nodeValue || !GLOSS_RE.test(n.nodeValue)) return NodeFilter.FILTER_REJECT;
                    const p = n.parentElement;
                    if (!p || p.closest("script,style,svg,a,button,input,textarea,select,option,.gloss")) return NodeFilter.FILTER_REJECT;
                    return NodeFilter.FILTER_ACCEPT;
                }
            });
            const nodes = [];
            while (walker.nextNode()) nodes.push(walker.currentNode);
            nodes.forEach(node => {
                const parts = node.nodeValue.split(new RegExp(GLOSS_RE.source, "g"));
                if (parts.length < 2) return;
                const frag = document.createDocumentFragment();
                parts.forEach((part, i) => {
                    if (i % 2 === 1 && SG_GLOSSARY[part]) {
                        const s = document.createElement("span");
                        s.className = "gloss";
                        s.dataset.term = part;
                        s.textContent = part;
                        frag.appendChild(s);
                    } else if (part) {
                        frag.appendChild(document.createTextNode(part));
                    }
                });
                node.parentNode.replaceChild(frag, node);
            });
        } finally {
            glossAnnotating = false;
        }
    }

    function initGlossary() {
        // Fix: this element was previously referenced as an undeclared `hubPaneEl`, which threw a
        // ReferenceError and silently disabled the whole glossary. Resolve it by id here.
        const hubPane = document.getElementById("hub-pane");
        if (!hubPane) return;

        let glossTimer = null;
        new MutationObserver(() => {
            if (glossAnnotating) return;
            clearTimeout(glossTimer);
            glossTimer = setTimeout(() => annotateGlossary(hubPane), 250);
        }).observe(hubPane, { childList: true, subtree: true });
        annotateGlossary(hubPane);

        const glossTipHtml = g =>
            `<div style="font-weight:700; margin-bottom:2px;">${esc(g.dataset.term)}</div>`
            + `<div>${esc(SG_GLOSSARY[g.dataset.term] || "")}</div>`;
        hubPane.addEventListener("mouseover", e => {
            const g = e.target.closest(".gloss");
            if (g) showTip(glossTipHtml(g), e.clientX, e.clientY);
        });
        hubPane.addEventListener("mouseout", e => {
            if (e.target.closest(".gloss")) hideTip();
        });
        // Mobile: tap shows the explanation (no hover available); tapping elsewhere dismisses it
        hubPane.addEventListener("click", e => {
            const g = e.target.closest(".gloss");
            if (g) showTip(glossTipHtml(g), e.clientX, e.clientY);
            else hideTip();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initGlossary);
    } else {
        initGlossary();
    }
})();
