/* MerlionOS — Life-event journeys pane.
 *
 * A guided, ordered checklist for major Singapore life events. GET /api/life-events/journeys for the
 * grid; GET /api/life-events/journey/{key} for one journey. Each step links to an official page and,
 * where relevant, deep-links into another MerlionOS tool. Informational only; nothing is stored.
 * Mirrors the self-managing pane pattern of js/cpflife.js. */
(function () {
    "use strict";

    const LIST_API = "/api/life-events/journeys";
    const ONE_API = "/api/life-events/journey/";

    function esc(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
            ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }

    // Tools now live in two shared pane: Money Planner (Home Cost | CPF LIFE | Benefits) and Alerts &
    // Safety (My Alerts | Scam Checker). Each tool maps to its pane; openTool() opens the pane then
    // selects the specific tool via the pane's inner toggle.
    const TOOL_PANE = { benefits: "hub-money-pane", upfront: "hub-money-pane",
                        cpflife: "hub-money-pane", scam: "hub-safety-pane" };
    const TOOL_LABEL = { benefits: "Benefits Finder", upfront: "Home Cost",
                         cpflife: "CPF LIFE", scam: "Scam Checker" };

    function openTool(tool) {
        const pane = TOOL_PANE[tool];
        if (!pane) return;
        const btn = document.querySelector('.hub-sub-tab-btn[data-hub-sub-tab="' + pane + '"]');
        if (btn) btn.click();
        // Select the specific tool inside its shared pane.
        if ((tool === "upfront" || tool === "cpflife" || tool === "benefits") && window.MerlionMoney) {
            window.MerlionMoney.select(tool);
        } else if (tool === "scam" && window.MerlionSafety) {
            window.MerlionSafety.select("scam");
        }
    }

    const container = () => document.getElementById("hub-journeys-content");

    async function load() {
        const el = container();
        if (!el) return;
        el.innerHTML = `<div class="hub-card"><p style="margin:0; color:var(--text-muted);">Loading life events…</p></div>`;
        try {
            const res = await fetch(LIST_API);
            if (!res.ok) throw new Error(res.statusText);
            renderGrid(el, await res.json());
        } catch (err) {
            el.innerHTML = `<div class="hub-card"><p style="margin:0; color:var(--danger,#c0392b);">✗ ${esc(err.message)}</p></div>`;
        }
    }

    function renderGrid(el, d) {
        const cards = (d.journeys || []).map((j) => `
            <button class="life-card" data-key="${esc(j.key)}" style="text-align:left; cursor:pointer;
                border:1px solid var(--border); border-radius:10px; background:var(--bg-panel);
                padding:16px; display:flex; flex-direction:column; gap:6px;">
                <div style="font-size:22px; color:var(--primary);"><i class="fa-solid ${esc(j.icon)}"></i></div>
                <div style="font-weight:800; font-size:15px; color:var(--text-main);">${esc(j.title)}</div>
                <div style="font-size:12px; color:var(--text-muted);">${esc(j.tagline)}</div>
                <div style="font-size:11px; color:var(--text-subtle); margin-top:2px;">${j.steps} steps</div>
            </button>`).join("");
        el.innerHTML = `
            <div class="hub-card" style="margin-bottom:16px;">
                <h3><i class="fa-solid fa-signs-post"></i> Life-Event Journeys</h3>
                <p style="font-size:13px; color:var(--text-muted); margin:0;">
                    Hit a big life moment? Pick one below for a step-by-step checklist — what to do, who
                    to contact, and the MerlionOS tools that help. Nothing you view is stored.</p>
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:12px;">
                ${cards}
            </div>
            <div class="hub-card" style="background:transparent; margin-top:14px;">
                <div style="font-size:11px; color:var(--text-subtle); font-style:italic;">${esc(d.disclaimer)}</div>
            </div>`;
        el.querySelectorAll(".life-card").forEach((b) =>
            b.addEventListener("click", () => openJourney(b.getAttribute("data-key"))));
    }

    async function openJourney(key) {
        const el = container();
        el.innerHTML = `<div class="hub-card"><p style="margin:0; color:var(--text-muted);">Loading…</p></div>`;
        try {
            const res = await fetch(ONE_API + encodeURIComponent(key));
            if (!res.ok) throw new Error(res.statusText);
            renderJourney(el, await res.json());
            el.scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (err) {
            el.innerHTML = `<div class="hub-card"><p style="margin:0; color:var(--danger,#c0392b);">✗ ${esc(err.message)}</p></div>`;
        }
    }

    function renderJourney(el, d) {
        const steps = (d.steps || []).map((s, i) => stepCard(s, i + 1)).join("");
        el.innerHTML = `
            <a id="life-back" style="cursor:pointer; color:var(--primary); font-size:13px; font-weight:600;">
                <i class="fa-solid fa-arrow-left"></i> All life events</a>
            <div class="hub-card" style="margin:12px 0 16px; border-left:4px solid var(--primary); background:rgba(52,120,246,.06);">
                <h3 style="margin-top:0;"><i class="fa-solid ${esc(d.icon)}"></i> ${esc(d.title)}</h3>
                <p style="font-size:13px; color:var(--text-muted); margin:0;">${esc(d.intro)}</p>
            </div>
            ${steps}
            <div class="hub-card" style="background:transparent;">
                <div style="font-size:11px; color:var(--text-subtle); font-style:italic;">${esc(d.disclaimer)}</div>
            </div>`;
        document.getElementById("life-back").addEventListener("click", load);
        el.querySelectorAll("[data-open-tool]").forEach((b) =>
            b.addEventListener("click", () => openTool(b.getAttribute("data-open-tool"))));
    }

    function chip(text, muted) {
        if (!text || text === "—") return "";
        return `<span style="display:inline-block; font-size:11px; padding:2px 8px; border-radius:99px;
            background:var(--bg-panel); border:1px solid var(--border);
            color:var(--text-${muted ? "subtle" : "muted"}); margin-right:6px;">${esc(text)}</span>`;
    }

    function stepCard(s, n) {
        const ext = s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener"
            style="color:var(--primary); font-size:12px; font-weight:600; margin-right:14px;">
            <i class="fa-solid fa-up-right-from-square"></i> ${esc(s.link_label || "Official page")}</a>` : "";
        const tool = s.tool ? `<a data-open-tool="${esc(s.tool)}" style="cursor:pointer;
            color:var(--success,#1a7f3c); font-size:12px; font-weight:700;">
            <i class="fa-solid fa-arrow-right-to-bracket"></i> Open ${esc(TOOL_LABEL[s.tool] || s.tool)} in MerlionOS</a>` : "";
        return `<div class="hub-card" style="margin-bottom:10px; display:flex; gap:14px;">
            <div style="flex:0 0 28px; height:28px; border-radius:50%; background:var(--primary); color:#fff;
                font-weight:800; font-size:13px; display:flex; align-items:center; justify-content:center;">${n}</div>
            <div style="flex:1;">
                <div style="font-weight:700; font-size:14px; color:var(--text-main); margin-bottom:4px;">${esc(s.title)}</div>
                <div style="margin-bottom:6px;">${chip(s.agency)}${chip(s.timing, true)}</div>
                <div style="font-size:12.5px; color:var(--text-muted); margin-bottom:8px;">${esc(s.detail)}</div>
                <div>${ext}${tool}</div>
            </div>
        </div>`;
    }

    window.MerlionJourneys = { load };
})();
