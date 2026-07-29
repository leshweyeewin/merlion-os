// charts.js — Generic dependency-free inline-SVG chart engine for SG Hub.
// Extracted from hub.js so the dashboard controllers (still in hub.js) consume a standalone
// charting module. Exposes globals used by hub.js: the CHART_SERIES / CHART_CONTEXT / CHART_INK
// constants and chartTooltip / showChartTooltip / hideChartTooltip / chartTicks / renderLineChart /
// renderBarChart / renderScatterChart. Loaded as a classic script BEFORE hub.js; depends only on
// the global escapeHTML() from utils.js.

    // ==== SG Hub chart layer ====================================================
    // Dependency-free inline SVG charts. Colors follow the dataviz method: categorical slots
    // validated against this app's light surface (#f5f5f5) — aqua/yellow sit below 3:1
    // contrast there, so every multi-series chart carries direct end-labels as relief.
    const CHART_INK = { grid: "#e1e0d9", axis: "#c3c2b7", label: "#898781" };
    const CHART_SERIES = ["#2a78d6", "#1baf7a", "#eda100"]; // fixed categorical order, never cycled
    const CHART_CONTEXT = "#8a8987"; // de-emphasized context marks only — never a peer category

    let chartTooltipEl = null;
    function chartTooltip() {
        if (!chartTooltipEl) {
            chartTooltipEl = document.createElement("div");
            chartTooltipEl.style.cssText = "position:fixed; z-index:9999; pointer-events:none; background:var(--bg-panel); border:1px solid var(--border); border-radius:6px; padding:6px 10px; font-size:11.5px; color:var(--text-main); box-shadow:0 2px 10px rgba(0,0,0,0.14); display:none; max-width:280px; line-height:1.5;";
            document.body.appendChild(chartTooltipEl);
        }
        return chartTooltipEl;
    }
    function showChartTooltip(html, clientX, clientY) {
        const t = chartTooltip();
        t.innerHTML = html;
        t.style.display = "block";
        const pad = 12;
        const r = t.getBoundingClientRect();
        let x = clientX + pad, y = clientY + pad;
        if (x + r.width > window.innerWidth - 8) x = clientX - r.width - pad;
        if (y + r.height > window.innerHeight - 8) y = clientY - r.height - pad;
        
        // Clamp to prevent the tooltip from going off-screen on small viewports
        x = Math.max(8, Math.min(x, window.innerWidth - r.width - 8));
        y = Math.max(8, Math.min(y, window.innerHeight - r.height - 8));
        
        t.style.left = x + "px";
        t.style.top = y + "px";
    }
    function hideChartTooltip() { if (chartTooltipEl) chartTooltipEl.style.display = "none"; }

    function chartTicks(maxVal, count = 4) {
        const rawStep = maxVal / count;
        const mag = Math.pow(10, Math.floor(Math.log10(rawStep || 1)));
        const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= rawStep) || rawStep;
        const ticks = [];
        for (let v = 0; v <= maxVal + step * 0.001; v += step) ticks.push(Math.round(v * 100) / 100);
        if (ticks[ticks.length - 1] < maxVal) ticks.push(ticks[ticks.length - 1] + step);
        return ticks;
    }
    const fmtK = v => v >= 1000 ? ((v / 1000).toFixed(v >= 10000 ? 0 : 1).replace(/\.0$/, "")) + "k" : String(Math.round(v));

    function renderLineChart(el, { xLabels, series, height = 220, xTickEvery = 1, endLabels = true }) {
        const W = Math.max(el.clientWidth || 620, 320), H = height;
        const padL = 40, padR = endLabels ? 92 : 14, padT = 12, padB = 24;
        const iw = W - padL - padR, ih = H - padT - padB;
        const maxV = Math.max(...series.flatMap(s => s.values).filter(v => v != null), 1);
        const ticks = chartTicks(maxV);
        const topV = ticks[ticks.length - 1];
        const x = i => padL + (xLabels.length <= 1 ? iw / 2 : (i / (xLabels.length - 1)) * iw);
        const y = v => padT + ih - (v / topV) * ih;

        let g = "";
        ticks.forEach(t => {
            g += `<line x1="${padL}" y1="${y(t)}" x2="${padL + iw}" y2="${y(t)}" stroke="${CHART_INK.grid}" stroke-width="1"/>`
                + `<text x="${padL - 6}" y="${y(t) + 3.5}" text-anchor="end" font-size="10" fill="${CHART_INK.label}">${fmtK(t)}</text>`;
        });
        // The last label always renders (it's often a "Next X (Forecast)" point worth calling
        // out) — but a regular xTickEvery label landing right next to it would just overlap the
        // text, since neither one knows about the other's width. Rough-measure and skip labels
        // that would overlap with either the last label or the previously rendered label.
        const approxLabelHalfWidth = s => (String(s).length * 5.6 + 6) / 2;
        const lastIdx = xLabels.length - 1;
        const lastLabelHalfWidth = approxLabelHalfWidth(xLabels[lastIdx]);
        let lastRenderedX = -Infinity;
        let lastRenderedHalfW = 0;

        xLabels.forEach((lab, i) => {
            const isLast = i === lastIdx;
            if (!isLast) {
                if (i % xTickEvery !== 0) return;
                const thisX = x(i);
                const thisHalfW = approxLabelHalfWidth(lab);
                // Prevent overlapping with the last label
                if (x(lastIdx) - thisX < lastLabelHalfWidth + thisHalfW + 6) return;
                // Prevent overlapping with the previously rendered label
                if (thisX - lastRenderedX < lastRenderedHalfW + thisHalfW + 6) return;
                
                lastRenderedX = thisX;
                lastRenderedHalfW = thisHalfW;
            }
            g += `<text x="${x(i)}" y="${H - 8}" text-anchor="middle" font-size="10" fill="${CHART_INK.label}">${escapeHTML(lab)}</text>`;
        });
        g += `<line x1="${padL}" y1="${y(0)}" x2="${padL + iw}" y2="${y(0)}" stroke="${CHART_INK.axis}" stroke-width="1"/>`;
        series.forEach(s => {
            const pts = s.values.map((v, i) => v == null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`).filter(Boolean).join(" ");
            g += `<polyline points="${pts}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`;
        });
        if (endLabels) {
            const ends = series
                .map(s => ({ s, yy: y(s.values[s.values.length - 1] ?? 0) }))
                .sort((a, b) => a.yy - b.yy);
            let lastY = -Infinity;
            ends.forEach(e => {
                const ly = Math.max(e.yy, lastY + 13);
                lastY = ly;
                g += `<circle cx="${padL + iw + 3}" cy="${ly}" r="3.5" fill="${e.s.color}"/>`
                    + `<text x="${padL + iw + 10}" y="${ly + 3.5}" font-size="10.5" font-weight="600" fill="var(--text-main)">${escapeHTML(e.s.name)}</text>`;
            });
        }
        const legend = series.length > 1
            ? `<div style="display:flex; gap:14px; flex-wrap:wrap; font-size:11px; color:var(--text-main); padding:0 2px 6px;">`
            + series.map(s => `<span><span style="display:inline-block; width:9px; height:9px; border-radius:50%; background:${s.color}; margin-right:5px;"></span>${escapeHTML(s.name)}</span>`).join("")
            + `</div>`
            : "";
        el.innerHTML = legend + `<svg width="100%" viewBox="0 0 ${W} ${H}" style="display:block; font-family:inherit;">${g}<g class="hoverg"></g><rect class="overlay" x="${padL}" y="${padT}" width="${iw}" height="${ih}" fill="transparent"/></svg>`;
        const svg = el.querySelector("svg"), overlay = svg.querySelector(".overlay"), hoverg = svg.querySelector(".hoverg");
        overlay.addEventListener("mousemove", ev => {
            const rect = svg.getBoundingClientRect();
            const mx = (ev.clientX - rect.left) * (W / rect.width);
            const ci = Math.max(0, Math.min(xLabels.length - 1, Math.round(((mx - padL) / iw) * (xLabels.length - 1))));
            let hg = `<line x1="${x(ci)}" y1="${padT}" x2="${x(ci)}" y2="${padT + ih}" stroke="${CHART_INK.axis}" stroke-width="1" stroke-dasharray="3,3"/>`;
            let rows = "";
            series.forEach(s => {
                const v = s.values[ci];
                if (v == null) return;
                hg += `<circle cx="${x(ci)}" cy="${y(v)}" r="4.5" fill="${s.color}" stroke="#ffffff" stroke-width="2"/>`;
                rows += `<div><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${s.color}; margin-right:6px;"></span>${escapeHTML(s.name)}: <strong>${v.toLocaleString()}</strong></div>`;
            });
            hoverg.innerHTML = hg;
            showChartTooltip(`<div style="font-weight:700; margin-bottom:2px;">${escapeHTML(String(xLabels[ci]))}</div>` + rows, ev.clientX, ev.clientY);
        });
        overlay.addEventListener("mouseleave", () => { hoverg.innerHTML = ""; hideChartTooltip(); });

        const handleTouch = ev => {
            const touch = ev.touches[0];
            if (!touch) return;
            const rect = svg.getBoundingClientRect();
            const mx = (touch.clientX - rect.left) * (W / rect.width);
            const ci = Math.max(0, Math.min(xLabels.length - 1, Math.round(((mx - padL) / iw) * (xLabels.length - 1))));
            let hg = `<line x1="${x(ci)}" y1="${padT}" x2="${x(ci)}" y2="${padT + ih}" stroke="${CHART_INK.axis}" stroke-width="1" stroke-dasharray="3,3"/>`;
            let rows = "";
            series.forEach(s => {
                const v = s.values[ci];
                if (v == null) return;
                hg += `<circle cx="${x(ci)}" cy="${y(v)}" r="4.5" fill="${s.color}" stroke="#ffffff" stroke-width="2"/>`;
                rows += `<div><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${s.color}; margin-right:6px;"></span>${escapeHTML(s.name)}: <strong>${v.toLocaleString()}</strong></div>`;
            });
            hoverg.innerHTML = hg;
            showChartTooltip(`<div style="font-weight:700; margin-bottom:2px;">${escapeHTML(String(xLabels[ci]))}</div>` + rows, touch.clientX, touch.clientY);
            if (ev.cancelable) ev.preventDefault();
        };
        overlay.addEventListener("touchstart", handleTouch, { passive: false });
        overlay.addEventListener("touchmove", handleTouch, { passive: false });
        overlay.addEventListener("touchend", () => { hoverg.innerHTML = ""; hideChartTooltip(); });
    }

    function renderBarChart(el, { labels, values, height = 220, color = CHART_SERIES[0], tooltipFor }) {
        const W = Math.max(el.clientWidth || 460, 300), H = height;
        const padL = 34, padR = 8, padT = 18, padB = 26;
        const iw = W - padL - padR, ih = H - padT - padB;
        const maxV = Math.max(...values, 1);
        const ticks = chartTicks(maxV);
        const topV = ticks[ticks.length - 1];
        const y = v => padT + ih - (v / topV) * ih;
        const slot = iw / values.length, gap = Math.max(slot * 0.18, 2), bw = slot - gap;

        let g = "";
        ticks.forEach(t => {
            g += `<line x1="${padL}" y1="${y(t)}" x2="${padL + iw}" y2="${y(t)}" stroke="${CHART_INK.grid}" stroke-width="1"/>`
                + `<text x="${padL - 6}" y="${y(t) + 3.5}" text-anchor="end" font-size="10" fill="${CHART_INK.label}">${fmtK(t)}</text>`;
        });
        values.forEach((v, i) => {
            const bx = padL + i * slot + gap / 2;
            const by = y(v), bh = padT + ih - by;
            const r = Math.min(4, bw / 2, bh); // 4px rounded top, anchored square to the baseline
            g += `<path class="bar" data-i="${i}" d="M${bx},${by + bh} L${bx},${by + r} Q${bx},${by} ${bx + r},${by} L${bx + bw - r},${by} Q${bx + bw},${by} ${bx + bw},${by + r} L${bx + bw},${by + bh} Z" fill="${color}"/>`
                + `<text x="${bx + bw / 2}" y="${H - 8}" text-anchor="middle" font-size="9.5" fill="${CHART_INK.label}">${escapeHTML(labels[i])}</text>`;
        });
        const mi = values.indexOf(maxV);
        g += `<text x="${padL + mi * slot + slot / 2}" y="${y(maxV) - 5}" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--text-main)">${maxV.toLocaleString()}</text>`;
        g += `<line x1="${padL}" y1="${padT + ih}" x2="${padL + iw}" y2="${padT + ih}" stroke="${CHART_INK.axis}" stroke-width="1"/>`;
        el.innerHTML = `<svg width="100%" viewBox="0 0 ${W} ${H}" style="display:block; font-family:inherit;">${g}</svg>`;
        el.querySelectorAll(".bar").forEach(b => {
            b.addEventListener("mousemove", ev => showChartTooltip(tooltipFor(+b.dataset.i), ev.clientX, ev.clientY));
            b.addEventListener("mouseleave", hideChartTooltip);
            const handleTouch = ev => {
                const touch = ev.touches[0];
                if (!touch) return;
                showChartTooltip(tooltipFor(+b.dataset.i), touch.clientX, touch.clientY);
                if (ev.cancelable) ev.preventDefault();
            };
            b.addEventListener("touchstart", handleTouch, { passive: false });
            b.addEventListener("touchmove", handleTouch, { passive: false });
            b.addEventListener("touchend", hideChartTooltip);
        });
    }

    function renderScatterChart(el, { points, height = 250, xLabel, yLabel, xRef, quadrants }) {
        // points: {x, y, name, sub, highlight}; y clamped to [-50, 100] for position, true value in tooltip
        const W = Math.max(el.clientWidth || 460, 300), H = height;
        const padL = 40, padR = 12, padT = 14, padB = 30;
        const iw = W - padL - padR, ih = H - padT - padB;
        const Y_MIN = -50, Y_MAX = 100;
        const topX = chartTicks(Math.max(...points.map(p => p.x), 1)).pop();
        const px = v => padL + (v / topX) * iw;
        const py = v => padT + ih - ((Math.max(Y_MIN, Math.min(Y_MAX, v)) - Y_MIN) / (Y_MAX - Y_MIN)) * ih;

        let g = "";
        [-50, 0, 50, 100].forEach(t => {
            const heavy = t === 0;
            g += `<line x1="${padL}" y1="${py(t)}" x2="${padL + iw}" y2="${py(t)}" stroke="${heavy ? CHART_INK.axis : CHART_INK.grid}" stroke-width="1"/>`
                + `<text x="${padL - 6}" y="${py(t) + 3.5}" text-anchor="end" font-size="10" fill="${CHART_INK.label}">${t > 0 ? "+" : ""}${t}%</text>`;
        });
        chartTicks(topX).forEach(t => {
            g += `<text x="${px(t)}" y="${H - 14}" text-anchor="middle" font-size="10" fill="${CHART_INK.label}">${fmtK(t)}</text>`;
        });
        g += `<text x="${padL + iw / 2}" y="${H - 2}" text-anchor="middle" font-size="9.5" fill="${CHART_INK.label}">${escapeHTML(xLabel)}</text>`;
        if (xRef) {
            g += `<line x1="${px(xRef.value)}" y1="${padT}" x2="${px(xRef.value)}" y2="${padT + ih}" stroke="${CHART_INK.axis}" stroke-width="1" stroke-dasharray="4,3"/>`
                + `<text x="${px(xRef.value) + 5}" y="${padT + 10}" font-size="9.5" font-weight="600" fill="${CHART_INK.label}">${escapeHTML(xRef.label)}</text>`;
        }
        if (quadrants) {
            const qStyle = `font-size="9.5" font-weight="700" fill="${CHART_INK.label}"`;
            if (quadrants.tr) g += `<text x="${padL + iw - 6}" y="${padT + 10}" text-anchor="end" ${qStyle}>${escapeHTML(quadrants.tr)}</text>`;
            if (quadrants.tl) g += `<text x="${padL + 6}" y="${padT + 10}" ${qStyle}>${escapeHTML(quadrants.tl)}</text>`;
            if (quadrants.br) g += `<text x="${padL + iw - 6}" y="${padT + ih - 6}" text-anchor="end" ${qStyle}>${escapeHTML(quadrants.br)}</text>`;
            if (quadrants.bl) g += `<text x="${padL + 6}" y="${padT + ih - 6}" ${qStyle}>${escapeHTML(quadrants.bl)}</text>`;
        }
        const ordered = points.slice().sort((a, b) => (a.highlight ? 1 : 0) - (b.highlight ? 1 : 0)); // highlights drawn on top
        ordered.forEach(p => {
            g += p.highlight
                ? `<circle cx="${px(p.x).toFixed(1)}" cy="${py(p.y).toFixed(1)}" r="4" fill="${CHART_SERIES[0]}" stroke="#ffffff" stroke-width="1.5"/>`
                : `<circle cx="${px(p.x).toFixed(1)}" cy="${py(p.y).toFixed(1)}" r="3" fill="${CHART_CONTEXT}" fill-opacity="0.55"/>`;
        });
        el.innerHTML = `<svg width="100%" viewBox="0 0 ${W} ${H}" style="display:block; font-family:inherit;">${g}<g class="hoverg"></g><rect class="overlay" x="${padL}" y="${padT}" width="${iw}" height="${ih}" fill="transparent"/></svg>`;
        const svg = el.querySelector("svg"), overlay = svg.querySelector(".overlay"), hoverg = svg.querySelector(".hoverg");
        overlay.addEventListener("mousemove", ev => {
            const rect = svg.getBoundingClientRect();
            const scale = W / rect.width;
            const mx = (ev.clientX - rect.left) * scale, my = (ev.clientY - rect.top) * scale;
            let bestD = 14 * 14, best = null;
            points.forEach(p => {
                const dx = px(p.x) - mx, dy = py(p.y) - my, d = dx * dx + dy * dy;
                if (d < bestD) { bestD = d; best = p; }
            });
            if (!best) { hoverg.innerHTML = ""; hideChartTooltip(); return; }
            hoverg.innerHTML = `<circle cx="${px(best.x)}" cy="${py(best.y)}" r="6" fill="${best.highlight ? CHART_SERIES[0] : CHART_CONTEXT}" stroke="#ffffff" stroke-width="2"/>`;
            const clamped = best.y > Y_MAX || best.y < Y_MIN;
            showChartTooltip(
                `<div style="font-weight:700; margin-bottom:2px;">${escapeHTML(best.name)}</div>`
                + (best.sub ? `<div style="color:var(--text-muted); font-size:10.5px;">${escapeHTML(best.sub)}</div>` : "")
                + `<div>S$${best.x.toLocaleString()}/mth · <strong>${best.y >= 0 ? "+" : ""}${best.y.toFixed(1)}%</strong> YoY${clamped ? " (beyond chart scale)" : ""}</div>`,
                ev.clientX, ev.clientY);
        });
        overlay.addEventListener("mouseleave", () => { hoverg.innerHTML = ""; hideChartTooltip(); });

        const handleTouch = ev => {
            const touch = ev.touches[0];
            if (!touch) return;
            const rect = svg.getBoundingClientRect();
            const scale = W / rect.width;
            const mx = (touch.clientX - rect.left) * scale, my = (touch.clientY - rect.top) * scale;
            let bestD = 14 * 14, best = null;
            points.forEach(p => {
                const dx = px(p.x) - mx, dy = py(p.y) - my, d = dx * dx + dy * dy;
                if (d < bestD) { bestD = d; best = p; }
            });
            if (!best) { hoverg.innerHTML = ""; hideChartTooltip(); return; }
            hoverg.innerHTML = `<circle cx="${px(best.x)}" cy="${py(best.y)}" r="6" fill="${best.highlight ? CHART_SERIES[0] : CHART_CONTEXT}" stroke="#ffffff" stroke-width="2"/>`;
            const clamped = best.y > Y_MAX || best.y < Y_MIN;
            showChartTooltip(
                `<div style="font-weight:700; margin-bottom:2px;">${escapeHTML(best.name)}</div>`
                + (best.sub ? `<div style="color:var(--text-muted); font-size:10.5px;">${escapeHTML(best.sub)}</div>` : "")
                + `<div>S$${best.x.toLocaleString()}/mth · <strong>${best.y >= 0 ? "+" : ""}${best.y.toFixed(1)}%</strong> YoY${clamped ? " (beyond chart scale)" : ""}</div>`,
                touch.clientX, touch.clientY);
            if (ev.cancelable) ev.preventDefault();
        };
        overlay.addEventListener("touchstart", handleTouch, { passive: false });
        overlay.addEventListener("touchmove", handleTouch, { passive: false });
        overlay.addEventListener("touchend", () => { hoverg.innerHTML = ""; hideChartTooltip(); });
    }
    // ==== end chart layer =======================================================
