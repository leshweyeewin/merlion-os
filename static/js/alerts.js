/* MerlionOS — My Alerts pane (watchlists + notifications + Web Push + Telegram pairing).
 *
 * Identity is a browser-generated client_id kept in localStorage (there are no accounts). Every
 * request is scoped to it, so a browser only ever sees its own watches. The pane re-renders on each
 * tab visit; an unread-count poll keeps the tab badge live even while you're on another tab. */
(function () {
    "use strict";

    const API = "/api/alerts";
    const CID_KEY = "merlion_client_id";

    // i18n helpers — chrome via the hub dictionary (window.hubT); backend prose (notification titles/
    // bodies, watch labels) via the shared on-demand Translate button (window.MerlionProse). fmt() fills
    // {placeholder} tokens. All fall back gracefully if translations/helpers haven't loaded yet.
    const T = (k) => (window.hubT ? window.hubT(k) : k);
    const fmt = (s, v) => s.replace(/\{(\w+)\}/g, (m, k) => (v && k in v) ? v[k] : m);
    const pb = (s) => (window.MerlionProse ? window.MerlionProse.block(s) : esc(s));
    const bindProse = (el) => { if (window.MerlionProse && el) window.MerlionProse.bind(el); };

    function clientId() {
        let id = localStorage.getItem(CID_KEY);
        if (!id) {
            id = (crypto.randomUUID ? crypto.randomUUID() : "cid-" + Math.random().toString(36).slice(2) + Date.now());
            localStorage.setItem(CID_KEY, id);
        }
        return id;
    }

    function esc(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
            ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }

    // ── watch-type field specs (mirror tools/alerts.py validators) ────────────────────────────
    const MRT_LINES = [
        ["EWL", "East-West Line"], ["NSL", "North-South Line"], ["NEL", "North-East Line"],
        ["CCL", "Circle Line"], ["DTL", "Downtown Line"], ["TEL", "Thomson-East Coast Line"],
        ["BPLRT", "Bukit Panjang LRT"], ["SLRT", "Sengkang LRT"], ["PLRT", "Punggol LRT"],
    ];

    // Each returns the inner HTML for its param fields; readers pull values back out by element id.
    const WATCH_FORMS = {
        coe: () => `
            <label>${esc(T("al-f-category"))} ${sel("wf-coe-cat", ["A", "B", "C", "D", "E"].map(c => [c, T("al-f-cat") + " " + c]))}</label>
            <label>${esc(T("al-f-when-premium"))}
                ${sel("wf-coe-dir", [["below", T("al-f-below")], ["above", T("al-f-above")]])}
                S$ <input id="wf-coe-thr" type="number" min="1000" max="300000" step="1000" value="90000" style="${INP}">
            </label>`,
        psi: () => `<label>${esc(T("al-f-psi-above"))}
            <input id="wf-psi-thr" type="number" min="20" max="400" value="100" style="${INP}"></label>`,
        mrt: () => `<label>${esc(T("al-f-line"))} ${sel("wf-mrt-line", MRT_LINES)}</label>`,
        resale: () => `
            <label>${esc(T("al-f-town"))} <input id="wf-resale-town" type="text" placeholder="${esc(T("al-f-town-eg-tampines"))}" style="${INP}"></label>
            <label>${esc(T("al-f-moves-more"))} <input id="wf-resale-pct" type="number" min="1" max="50" value="3" style="${INP}"> %</label>`,
        bto: () => `<label>${esc(T("al-f-town"))} <input id="wf-bto-town" type="text" placeholder="${esc(T("al-f-town-eg-punggol"))}" style="${INP}"></label>`,
        iras: () => `<label>${esc(T("al-f-iras-within"))}
            <input id="wf-iras-days" type="number" min="1" max="90" value="14" style="${INP}"> ${esc(T("al-f-days"))}</label>`,
    };

    const WATCH_READERS = {
        coe: () => ({ category: val("wf-coe-cat"), direction: val("wf-coe-dir"), threshold: num("wf-coe-thr") }),
        psi: () => ({ threshold: num("wf-psi-thr") }),
        mrt: () => ({ line_code: val("wf-mrt-line") }),
        resale: () => ({ town: val("wf-resale-town"), threshold_pct: num("wf-resale-pct") }),
        bto: () => ({ town: val("wf-bto-town") }),
        iras: () => ({ days_before: num("wf-iras-days") }),
    };

    const INP = "padding:5px 8px; border:1px solid var(--border); border-radius:6px; background:var(--bg-panel); color:var(--text-main); font-size:13px; width:110px;";

    function sel(id, opts) {
        return `<select id="${id}" style="${INP} width:auto;">` +
            opts.map(([v, label]) => `<option value="${esc(v)}">${esc(label)}</option>`).join("") + "</select>";
    }
    const val = (id) => (document.getElementById(id) || {}).value || "";
    const num = (id) => parseInt(val(id), 10);

    // ── networking ────────────────────────────────────────────────────────────────────────────
    async function api(path, opts) {
        const res = await fetch(API + path, opts);
        if (!res.ok) {
            let detail = res.statusText;
            try { detail = (await res.json()).detail || detail; } catch (e) { /* ignore */ }
            throw new Error(detail);
        }
        return res.status === 204 ? null : res.json();
    }

    let CONFIG = null;
    async function getConfig() {
        if (!CONFIG) CONFIG = await api("/config");
        return CONFIG;
    }

    // ── render ────────────────────────────────────────────────────────────────────────────────
    const container = () => document.getElementById("hub-alerts-content");

    async function load() {
        const el = container();
        if (!el) return;
        try {
            const cfg = await getConfig();
            const data = await api("?client_id=" + encodeURIComponent(clientId()));
            render(el, cfg, data);
            updateBadge(data.unread_count);
        } catch (err) {
            el.innerHTML = `<div class="hub-card"><p style="color:var(--danger,#c0392b);margin:0;">
                ${esc(T("al-load-error"))} ${esc(err.message)}</p></div>`;
        }
    }

    // reload() re-fetches + re-renders the pane in the current language. Called by hub.js on
    // merlion:languagechange (the pane already re-fetches on every visit, so this just refreshes chrome).
    function reload() { if (container()) load(); }

    function render(el, cfg, data) {
        const typeOptions = cfg.watch_types.map(t => [t.key, t.label]);
        const firstKey = cfg.watch_types[0].key;

        const subRows = (data.subscriptions || []).map(s => `
            <div style="display:flex; align-items:center; gap:10px; padding:8px 0; border-bottom:1px solid var(--border);">
                <span style="flex:1; font-size:13px; color:var(--text-main);">🔔 ${pb(s.label)}</span>
                <button data-del="${esc(s.id)}" class="alerts-del-btn"
                    style="background:none; border:1px solid var(--border); color:var(--text-muted); border-radius:6px; padding:3px 9px; font-size:12px; cursor:pointer;">${esc(T("al-remove"))}</button>
            </div>`).join("") ||
            `<p style="color:var(--text-subtle); margin:0; font-size:13px;">${esc(T("al-no-watches"))}</p>`;

        const notifRows = (data.notifications || []).map(n => `
            <div style="padding:9px 0; border-bottom:1px solid var(--border); ${n.read_at ? "opacity:.6;" : ""}">
                <div style="font-weight:700; font-size:13px; color:var(--text-main);">${n.read_at ? "" : "🟢 "}${pb(n.title)}</div>
                <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">${pb(n.body)}</div>
                <div style="font-size:10px; color:var(--text-subtle); margin-top:3px;">${fmtTime(n.created_at)}</div>
            </div>`).join("") ||
            `<p style="color:var(--text-subtle); margin:0; font-size:13px;">${esc(T("al-nothing-yet"))}</p>`;

        el.innerHTML = `
        <div class="hub-card" style="margin-bottom:18px;">
            <h3><i class="fa-solid fa-plus"></i> ${esc(T("al-create-title"))}</h3>
            <p style="font-size:13px; color:var(--text-muted); margin-bottom:12px;">
                ${esc(T("al-create-desc"))}</p>
            <div style="display:flex; flex-wrap:wrap; align-items:flex-end; gap:10px;">
                <label style="font-size:13px; color:var(--text-main);">${esc(T("al-watch"))}
                    ${sel("wf-type", typeOptions)}</label>
                <div id="wf-fields" style="display:flex; flex-wrap:wrap; align-items:center; gap:8px; font-size:13px; color:var(--text-main);"></div>
                <button id="wf-save" style="background:var(--primary); color:#fff; border:none; border-radius:6px; padding:7px 16px; font-weight:700; font-size:13px; cursor:pointer;">${esc(T("al-add"))}</button>
            </div>
            <div id="wf-msg" style="font-size:12px; margin-top:8px;"></div>
        </div>

        <div class="hub-card" style="margin-bottom:18px;">
            <h3><i class="fa-solid fa-satellite-dish"></i> ${esc(T("al-delivery-title"))}</h3>
            <p style="font-size:13px; color:var(--text-muted); margin-bottom:12px;">
                ${esc(T("al-delivery-desc"))}</p>
            <div style="display:flex; flex-wrap:wrap; gap:10px;">
                <button id="wf-push" style="border:1px solid var(--border); background:var(--bg-panel); color:var(--text-main); border-radius:6px; padding:7px 14px; font-size:13px; cursor:pointer;">
                    <i class="fa-solid fa-bell"></i> ${esc(T("al-enable-push"))}</button>
                ${cfg.channels.telegram ? `<button id="wf-tele" style="border:1px solid var(--border); background:var(--bg-panel); color:var(--text-main); border-radius:6px; padding:7px 14px; font-size:13px; cursor:pointer;">
                    <i class="fa-brands fa-telegram"></i> ${esc(T("al-link-tele"))}</button>` : ""}
            </div>
            <div id="wf-channel-msg" style="font-size:12px; margin-top:8px; color:var(--text-muted);"></div>
        </div>

        <div class="hub-card" style="margin-bottom:18px;">
            <h3><i class="fa-solid fa-list-check"></i> ${esc(T("al-your-watches"))}</h3>
            <div style="margin-top:8px;">${subRows}</div>
        </div>

        <div class="hub-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0;"><i class="fa-solid fa-inbox"></i> ${esc(T("al-notifications"))}</h3>
                <button id="wf-read" style="background:none; border:1px solid var(--border); color:var(--text-muted); border-radius:6px; padding:4px 10px; font-size:12px; cursor:pointer;">${esc(T("al-mark-read"))}</button>
            </div>
            <div style="margin-top:10px;">${notifRows}</div>
        </div>`;
        bindProse(el);

        // Wire the dynamic param fields + all buttons.
        const fields = document.getElementById("wf-fields");
        const typeSel = document.getElementById("wf-type");
        const renderFields = () => { fields.innerHTML = WATCH_FORMS[typeSel.value](); };
        renderFields();
        typeSel.addEventListener("change", renderFields);

        document.getElementById("wf-save").addEventListener("click", () => addAlert(typeSel.value));
        document.getElementById("wf-read").addEventListener("click", markRead);
        document.getElementById("wf-push").addEventListener("click", enablePush);
        const tele = document.getElementById("wf-tele");
        if (tele) tele.addEventListener("click", linkTelegram);
        el.querySelectorAll(".alerts-del-btn").forEach(b =>
            b.addEventListener("click", () => removeAlert(b.getAttribute("data-del"))));

        void firstKey;
    }

    // ── actions ───────────────────────────────────────────────────────────────────────────────
    async function addAlert(type) {
        const msg = document.getElementById("wf-msg");
        let params;
        try {
            params = WATCH_READERS[type]();
        } catch (e) { return; }
        msg.textContent = T("al-adding");
        msg.style.color = "var(--text-muted)";
        try {
            await api("", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ client_id: clientId(), watch_type: type, params }),
            });
            msg.textContent = T("al-added");
            msg.style.color = "var(--success,#1a7f3c)";
            load();
        } catch (err) {
            msg.textContent = "✗ " + err.message;
            msg.style.color = "var(--danger,#c0392b)";
        }
    }

    async function removeAlert(id) {
        try {
            await api("/" + encodeURIComponent(id) + "?client_id=" + encodeURIComponent(clientId()), { method: "DELETE" });
            load();
        } catch (err) { /* surfaced on next load */ }
    }

    async function markRead() {
        try {
            await api("/read", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ client_id: clientId() }),
            });
            load();
        } catch (err) { /* ignore */ }
    }

    // ── Web Push ──────────────────────────────────────────────────────────────────────────────
    function urlB64ToUint8Array(base64) {
        const padding = "=".repeat((4 - (base64.length % 4)) % 4);
        const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
        const raw = atob(b64);
        return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
    }

    async function enablePush() {
        const msg = document.getElementById("wf-channel-msg");
        const cfg = await getConfig();
        if (!cfg.channels.webpush || !cfg.channels.vapid_public_key) {
            msg.textContent = "Browser push isn't configured on this server yet (no VAPID key).";
            return;
        }
        if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
            msg.textContent = "This browser doesn't support push notifications.";
            return;
        }
        try {
            const perm = await Notification.requestPermission();
            if (perm !== "granted") { msg.textContent = "Notifications permission was denied."; return; }
            const reg = await navigator.serviceWorker.register("/sw.js");
            await navigator.serviceWorker.ready;
            const sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlB64ToUint8Array(cfg.channels.vapid_public_key),
            });
            await api("/channels/webpush", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ client_id: clientId(), subscription: sub.toJSON() }),
            });
            msg.textContent = "✓ Browser notifications enabled on this device.";
            msg.style.color = "var(--success,#1a7f3c)";
        } catch (err) {
            msg.textContent = "Couldn't enable push: " + err.message;
        }
    }

    async function linkTelegram() {
        const msg = document.getElementById("wf-channel-msg");
        try {
            const res = await api("/telegram/pair", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ client_id: clientId() }),
            });
            if (res.bot) {
                const deepLink = `https://t.me/${encodeURIComponent(res.bot)}?start=${encodeURIComponent(res.code)}`;
                msg.innerHTML = `<a href="${esc(deepLink)}" target="_blank" rel="noopener" style="color:var(--primary); font-weight:700;">
                    Open @${esc(res.bot)} in Telegram</a> and tap Start — or send the code
                    <strong style="font-size:15px;">${esc(res.code)}</strong> manually (valid 10 min).`;
            } else {
                msg.innerHTML = `Open Telegram, message the MerlionOS bot and send: <strong style="font-size:15px;">${esc(res.code)}</strong> (valid 10 min).`;
            }
        } catch (err) {
            msg.textContent = "Couldn't start Telegram linking: " + err.message;
        }
    }

    // ── unread badge on the tab ───────────────────────────────────────────────────────────────
    function updateBadge(count) {
        const badge = document.getElementById("alerts-tab-badge");
        if (!badge) return;
        if (count > 0) {
            badge.textContent = count > 99 ? "99+" : String(count);
            badge.classList.remove("hidden");
        } else {
            badge.classList.add("hidden");
        }
    }

    async function pollUnread() {
        try {
            const data = await api("?client_id=" + encodeURIComponent(clientId()));
            updateBadge(data.unread_count);
        } catch (err) { /* ignore transient poll errors */ }
    }

    function fmtTime(epochSeconds) {
        try {
            return new Date(epochSeconds * 1000).toLocaleString("en-SG",
                { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: true }) + " SGT";
        } catch (e) { return ""; }
    }

    // Poll the unread count periodically so the badge stays live without opening the pane.
    setInterval(pollUnread, 60000);
    document.addEventListener("DOMContentLoaded", pollUnread);

    window.MerlionAlerts = { load, reload };
})();
