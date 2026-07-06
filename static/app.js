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

document.addEventListener("DOMContentLoaded", () => {
    initPortalReordering();

    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const logsContainer = document.getElementById("logs-container");
    const suggestionChips = document.querySelectorAll(".suggestion-chip");
    
    // Collapsible Chat Widget DOM elements
    const chatTrigger = document.getElementById("chat-trigger");
    const chatWidget = document.getElementById("chat-widget");
    const minimizeBtn = document.getElementById("minimize-btn");
    const tabButtons = document.querySelectorAll(".tab-btn");
    const widgetPanes = document.querySelectorAll(".widget-pane");

    // Conversation history for multi-turn context (kept client-side)
    const conversationHistory = [];

    // Toggle Chat Widget open/close
    chatTrigger.addEventListener("click", () => {
        chatWidget.classList.remove("hidden");
        chatTrigger.style.display = "none";
        scrollToBottom();
        userInput.focus();
    });

    minimizeBtn.addEventListener("click", () => {
        chatWidget.classList.add("hidden");
        chatTrigger.style.display = "flex";
    });

    // Tab switcher logic
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            // Set active button class
            tabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            // Toggle panes visibility
            const targetPaneId = btn.getAttribute("data-tab");
            widgetPanes.forEach(pane => {
                if (pane.id === targetPaneId) {
                    pane.classList.remove("hidden");
                } else {
                    pane.classList.add("hidden");
                }
            });
            scrollToBottom();
        });
    });

    // Format operational logs timestamps
    function getTimestamp() {
        const now = new Date();
        return `[${now.toTimeString().split(' ')[0]}]`;
    }

    // Custom lightweight markdown renderer to safely format agent outputs
    function renderMarkdown(text) {
        if (!text) return "";
        
        // Escape HTML
        let html = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Bold text: **bold**
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

        // Inline code: `code`
        html = html.replace(/`(.*?)`/g, "<code>$1</code>");

        // Links: [label](url) — block javascript: and data: scheme hrefs to prevent XSS
        html = html.replace(/\[(.*?)\]\((.*?)\)/g, (match, label, url) => {
            return `<a href="${safeURL(url)}" target="_blank" rel="noopener noreferrer">${label}</a>`;
        });

        // Lists: lines starting with * or -
        let lines = html.split('\n');
        let inList = false;
        let processedLines = [];

        lines.forEach(line => {
            const listMatch = line.match(/^\s*[-*]\s+(.*)$/);
            if (listMatch) {
                if (!inList) {
                    processedLines.push('<ul>');
                    inList = true;
                }
                processedLines.push(`<li>${listMatch[1]}</li>`);
            } else {
                if (inList) {
                    processedLines.push('</ul>');
                    inList = false;
                }
                processedLines.push(line);
            }
        });
        if (inList) processedLines.push('</ul>');

        html = processedLines.join('\n');

        // Paragraph linebreaks
        html = html.split('\n\n').map(p => {
            if (p.trim().startsWith('<ul>') || p.trim().startsWith('<li>')) {
                return p;
            }
            return `<p>${p.replace(/\n/g, '<br>')}</p>`;
        }).join('');

        return html;
    }

    // Scroll chat and log windows to bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    // Append log entries to the Operations control panel
    function appendLog(type, tagText, message, details = null) {
        const logEntry = document.createElement("div");
        logEntry.className = `log-entry ${type}-entry`;

        const timeSpan = document.createElement("span");
        timeSpan.className = "log-time";
        timeSpan.textContent = getTimestamp();
        logEntry.appendChild(timeSpan);

        const tagSpan = document.createElement("span");
        tagSpan.className = `log-tag tag-${type}`;
        tagSpan.textContent = tagText;
        logEntry.appendChild(tagSpan);

        const textSpan = document.createElement("span");
        textSpan.className = "log-text";
        // message is pre-escaped by the caller — safe to set via innerHTML
        textSpan.innerHTML = message;
        logEntry.appendChild(textSpan);

        if (details) {
            const detailBlock = document.createElement("pre");
            detailBlock.className = "log-detail";
            detailBlock.textContent = typeof details === 'string' ? details : JSON.stringify(details, null, 2);
            logEntry.appendChild(detailBlock);
        }

        logsContainer.appendChild(logEntry);
        scrollToBottom();
    }

    // Render typing status indicator
    function showTypingIndicator() {
        const indicator = document.createElement("div");
        indicator.className = "message bot-message typing-container";
        indicator.id = "typing-indicator";
        indicator.innerHTML = `
            <div class="message-avatar"><i class="fa-solid fa-landmark"></i></div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        chatMessages.appendChild(indicator);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById("typing-indicator");
        if (indicator) indicator.remove();
    }

    // Send query message to FastAPI backend
    async function sendMessage(text) {
        if (!text.trim()) return;

        // Render user message bubble
        const userMsg = document.createElement("div");
        userMsg.className = "message user-message";
        userMsg.innerHTML = `
            <div class="message-avatar"><i class="fa-solid fa-user"></i></div>
            <div class="message-content">
                <p>${text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p>
            </div>
        `;
        chatMessages.appendChild(userMsg);
        scrollToBottom();

        // Clear input field and toggle typing loader
        userInput.value = "";
        userInput.disabled = true;
        showTypingIndicator();

        appendLog("system", "agent", `User initiated query parameter matching: "${text}"`);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, history: conversationHistory })
            });

            if (!response.ok) {
                if (response.status === 429) {
                    const body = await response.json().catch(() => ({}));
                    const err = new Error(body.detail || "Rate limit reached. Please wait a minute and try again.");
                    err.isRateLimit = true;
                    throw err;
                }
                throw new Error(`HTTP Error Status: ${response.status}`);
            }

            const data = await response.json();
            removeTypingIndicator();

            // Populate system operations logs
            if (data.logs && data.logs.length > 0) {
                data.logs.forEach(log => {
                    let logType = "system";
                    let tagLabel = "integration";
                    
                    if (log.tool === "search_singapore_government") {
                        logType = "search";
                        tagLabel = "search";
                        // No user-derived values interpolated — safe plain text message
                        appendLog(logType, tagLabel, `Executed directory lookup search for matched query`, {
                            arguments: log.arguments,
                            results: log.result
                        });
                    } else if (log.tool === "scrape_government_page") {
                        logType = "scrape";
                        tagLabel = "scrape";
                        // Escape the URL (user-supplied / model-echoed) before inserting into innerHTML
                        const safeUrl = escapeHTML(log.arguments.url || "");
                        appendLog(logType, tagLabel, `Scraped official content matching: <code>${safeUrl}</code>`, {
                            extracted_char_count: log.result.length,
                            content_preview: log.result.substring(0, 300) + "..."
                        });
                    } else {
                        // Escape tool name (model-controlled string) before inserting into innerHTML
                        const safeTool = escapeHTML(log.tool || "");
                        appendLog(logType, tagLabel, `Intercepted static database query: <code>${safeTool}</code>`, {
                            arguments: log.arguments,
                            result: log.result
                        });
                    }
                });
            } else {
                appendLog("system", "agent", "No tool execution required. Query answered using semantic instructions.");
            }

            // Render bot message response bubble
            const botMsg = document.createElement("div");
            botMsg.className = "message bot-message";
            botMsg.innerHTML = `
                <div class="message-avatar"><i class="fa-solid fa-landmark"></i></div>
                <div class="message-content">
                    ${renderMarkdown(data.response)}
                </div>
            `;
            chatMessages.appendChild(botMsg);
            
            appendLog("system", "success", "Response compiled and formatted successfully.");

            // Update conversation history for multi-turn context
            conversationHistory.push({ role: "user",  content: text });
            conversationHistory.push({ role: "model", content: data.response });

        } catch (error) {
            removeTypingIndicator();
            appendLog("error", "error", `API handshake failed: ${escapeHTML(error.message)}`);

            const errorMsg = document.createElement("div");
            errorMsg.className = "message bot-message";
            if (error.isRateLimit) {
                errorMsg.innerHTML = `
                    <div class="message-avatar"><i class="fa-solid fa-landmark"></i></div>
                    <div class="message-content">
                        <p style="color: var(--text-warning);"><i class="fa-solid fa-clock"></i> <strong>Rate Limited:</strong> ${escapeHTML(error.message)}</p>
                    </div>
                `;
            } else {
                errorMsg.innerHTML = `
                    <div class="message-avatar"><i class="fa-solid fa-landmark"></i></div>
                    <div class="message-content">
                        <p style="color: var(--text-error);"><i class="fa-solid fa-triangle-exclamation"></i> <strong>Execution Error:</strong> Failed to fetch guidance coordinates. Please check your network or server logs.</p>
                    </div>
                `;
            }
            chatMessages.appendChild(errorMsg);
        } finally {
            userInput.disabled = false;
            userInput.focus();
            scrollToBottom();
        }
    }

    // Submit listener
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = userInput.value;
        sendMessage(text);
    });

    // Preset suggestion pills listener
    suggestionChips.forEach(chip => {
        chip.addEventListener("click", () => {
            sendMessage(chip.getAttribute("data-query"));
        });
    });
});

// Drag-and-drop reordering of the portal directory grid, persisted in localStorage
function initPortalReordering() {
    const STORAGE_KEY = "merlionos-portal-order";
    const grid = document.querySelector(".grid-container");
    const resetBtn = document.getElementById("reset-layout-btn");
    if (!grid) return;

    const defaultOrder = Array.from(grid.querySelectorAll(".service-card")).map(card => card.dataset.agency);
    let draggedCard = null;
    let swapTarget = null;

    function applyOrder(order) {
        const cards = Array.from(grid.querySelectorAll(".service-card"));
        const cardsByAgency = new Map(cards.map(card => [card.dataset.agency, card]));
        order.forEach(agency => {
            const card = cardsByAgency.get(agency);
            if (card) grid.appendChild(card);
        });
    }

    function saveOrder() {
        const order = Array.from(grid.querySelectorAll(".service-card")).map(card => card.dataset.agency);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(order));
    }

    function loadSavedOrder() {
        try {
            const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
            if (Array.isArray(saved) && saved.length) {
                applyOrder(saved);
            }
        } catch (e) {
            // Ignore malformed/corrupted saved layout and keep default order
        }
    }

    // Nearest card to the pointer, by center-to-center distance (grid-aware, not just row-aware)
    function getClosestCard(container, x, y) {
        const cards = container.querySelectorAll(".service-card:not(.dragging)");
        let closest = null;
        let closestDist = Infinity;
        cards.forEach(card => {
            const box = card.getBoundingClientRect();
            const dx = x - (box.left + box.width / 2);
            const dy = y - (box.top + box.height / 2);
            const dist = dx * dx + dy * dy;
            if (dist < closestDist) {
                closestDist = dist;
                closest = card;
            }
        });
        return closest;
    }

    // Swap two cards' positions in the grid, wherever they are
    function swapCards(cardA, cardB) {
        const parent = cardA.parentNode;
        const placeholder = document.createComment("drag-swap-placeholder");
        parent.insertBefore(placeholder, cardA);
        parent.insertBefore(cardA, cardB);
        parent.insertBefore(cardB, placeholder);
        parent.removeChild(placeholder);
    }

    function clearSwapTarget() {
        if (swapTarget) swapTarget.classList.remove("drag-over");
        swapTarget = null;
    }

    grid.addEventListener("dragstart", (e) => {
        const card = e.target.closest(".service-card");
        if (!card) return;
        draggedCard = card;
        card.classList.add("dragging");
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", card.dataset.agency || "");
    });

    grid.addEventListener("dragend", () => {
        if (draggedCard) draggedCard.classList.remove("dragging");
        draggedCard = null;
        clearSwapTarget();
    });

    grid.addEventListener("dragover", (e) => {
        if (!draggedCard) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";

        const target = getClosestCard(grid, e.clientX, e.clientY);
        if (target === swapTarget) return;

        clearSwapTarget();
        if (target && target !== draggedCard) {
            swapTarget = target;
            swapTarget.classList.add("drag-over");
        }
    });

    grid.addEventListener("dragleave", (e) => {
        if (e.target === grid || !grid.contains(e.relatedTarget)) {
            clearSwapTarget();
        }
    });

    grid.addEventListener("drop", (e) => {
        e.preventDefault();
        if (draggedCard && swapTarget && swapTarget !== draggedCard) {
            swapCards(draggedCard, swapTarget);
            saveOrder();
        }
        clearSwapTarget();
    });

    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            localStorage.removeItem(STORAGE_KEY);
            applyOrder(defaultOrder);
        });
    }

    loadSavedOrder();
}

// ── SG Hub Live Dashboard Data Loading ───────────────────────────────────
function initSgHub() {
    let sgHubLoaded = false;
    let sgHubJobsData = null;

    const mainTabHubBtn = document.getElementById("main-tab-hub-btn");
    const mainTabPortalsBtn = document.getElementById("main-tab-portals-btn");
    const mainTabButtons = document.querySelectorAll(".main-tab-btn");
    const mainPanes = document.querySelectorAll(".main-pane");

    const weatherContent = document.getElementById("hub-weather-content");
    const govEventsContent = document.getElementById("hub-gov-events-content");
    const communityEventsContent = document.getElementById("hub-community-events-content");
    const mrtEventsContent = document.getElementById("hub-mrt-events-content");
    const hdbLaunchesContent = document.getElementById("hub-hdb-launches");
    const hdbNewsContent = document.getElementById("hub-hdb-news");
    const jobsContent = document.getElementById("hub-jobs-content");
    const sectorTabButtons = document.querySelectorAll(".sector-tab-btn");

    // SG Hub sub-pane tab switching
    const hubSubTabButtons = document.querySelectorAll(".hub-sub-tab-btn");
    const hubSubPanes = document.querySelectorAll(".hub-sub-pane");

    hubSubTabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            // Reset active style class
            hubSubTabButtons.forEach(b => {
                b.classList.remove("active-hub-sub-tab");
            });
            // Apply active class
            btn.classList.add("active-hub-sub-tab");

            const targetPaneId = btn.getAttribute("data-hub-sub-tab");
            hubSubPanes.forEach(pane => {
                if (pane.id === targetPaneId) {
                    pane.classList.remove("hidden");
                } else {
                    pane.classList.add("hidden");
                }
            });

            // Dynamically load the selected pane data
            loadSgHubPaneData(targetPaneId);
        });
    });

    // Main page tab switcher
    mainTabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            // Reset active style class
            mainTabButtons.forEach(b => {
                b.classList.remove("active-main-tab");
            });
            // Apply active style class
            btn.classList.add("active-main-tab");

            const targetPaneId = btn.getAttribute("data-main-tab");
            mainPanes.forEach(pane => {
                if (pane.id === targetPaneId) {
                    pane.classList.remove("hidden");
                } else {
                    pane.classList.add("hidden");
                }
            });
        });
    });

    // CPF Grant Calculator binding
    const incomeInput = document.getElementById("hdb-income-input");
    const calcBtn = document.getElementById("calc-hdb-grant-btn");
    const calcResult = document.getElementById("hdb-grant-result");

    if (calcBtn && incomeInput && calcResult) {
        calcBtn.addEventListener("click", () => {
            const income = parseInt(incomeInput.value);
            if (isNaN(income) || income < 0) {
                calcResult.innerHTML = "⚠️ Please enter a valid household income.";
                return;
            }
            
            let grant = 0;
            if (income <= 1500) grant = 80000;
            else if (income <= 3000) grant = 65000;
            else if (income <= 4500) grant = 50000;
            else if (income <= 6000) grant = 35000;
            else if (income <= 7500) grant = 20000;
            else if (income <= 9000) grant = 10000;
            else grant = 0;

            if (grant > 0) {
                calcResult.innerHTML = `<span style="color:var(--text-success); font-size:14px; font-weight:700;">🎯 Estimated CPF Grant: S$${grant.toLocaleString()}</span><br>
                    <span style="font-size:11px; font-weight:normal; color:var(--text-muted); display:block; margin-top:2px;">Includes Enhanced CPF Housing Grant (EHG) eligibility.</span>`;
            } else {
                calcResult.innerHTML = `<span style="color:var(--text-error); font-size:14px; font-weight:700;">Estimated Grant: S$0</span><br>
                    <span style="font-size:11px; font-weight:normal; color:var(--text-muted); display:block; margin-top:2px;">Household average income exceeds the S$9,000 ceiling.</span>`;
            }
        });
    }

    const loadedSgHubPanes = {
        "hub-gov-transit-pane": false,
        "hub-hdb-pane": false,
        "hub-jobs-pane": false,
        "hub-community-pane": false,
        "hub-env-pane": false
    };

    function showPaneLoader(paneId) {
        if (paneId === "hub-gov-transit-pane") {
            mrtEventsContent.innerHTML = "<p style='color: var(--text-subtle); margin:0;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading transit advisories...</p>";
            govEventsContent.innerHTML = "<p style='color: var(--text-subtle); margin:0;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading official alerts...</p>";
        } else if (paneId === "hub-hdb-pane") {
            hdbLaunchesContent.innerHTML = "<p style='color: var(--text-subtle); margin:0;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading BTO listings...</p>";
            hdbNewsContent.innerHTML = "<p style='color: var(--text-subtle); margin:0;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading press releases...</p>";
        } else if (paneId === "hub-jobs-pane") {
            jobsContent.innerHTML = "<p style='color: var(--text-subtle); margin:0;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading jobs analysis...</p>";
        } else if (paneId === "hub-community-pane") {
            communityEventsContent.innerHTML = "<p style='color: var(--text-subtle); margin:0;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading community events...</p>";
        } else if (paneId === "hub-env-pane") {
            weatherContent.innerHTML = "<p style='color: var(--text-subtle); margin:0;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading Weather and PSI...</p>";
        }
    }

    function showPaneError(paneId) {
        if (paneId === "hub-gov-transit-pane") {
            mrtEventsContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load transit feeds.</p>";
            govEventsContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load official alerts.</p>";
        } else if (paneId === "hub-hdb-pane") {
            hdbLaunchesContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load BTO listings.</p>";
            hdbNewsContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load portal news.</p>";
        } else if (paneId === "hub-jobs-pane") {
            jobsContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load employment statistics.</p>";
            const retrenchmentHeadlineEl = document.getElementById("retrenchment-headline");
            const retrenchmentDetailsEl = document.getElementById("retrenchment-details");
            if (retrenchmentHeadlineEl) retrenchmentHeadlineEl.textContent = "N/A";
            if (retrenchmentDetailsEl) retrenchmentDetailsEl.innerHTML = "<span style='color: var(--text-error);'>⚠️ Failed to load retrenchment data.</span>";
        } else if (paneId === "hub-community-pane") {
            communityEventsContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load community feeds.</p>";
        } else if (paneId === "hub-env-pane") {
            weatherContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load environment metrics.</p>";
        }
    }

    async function loadSgHubPaneData(paneId) {
        if (loadedSgHubPanes[paneId]) return;
        
        let endpoint = "";
        if (paneId === "hub-gov-transit-pane") endpoint = "/api/sg-hub/gov-transit";
        else if (paneId === "hub-hdb-pane") endpoint = "/api/sg-hub/hdb";
        else if (paneId === "hub-jobs-pane") endpoint = "/api/sg-hub/jobs?sector=tech";
        else if (paneId === "hub-community-pane") endpoint = "/api/sg-hub/community";
        else if (paneId === "hub-env-pane") endpoint = "/api/sg-hub/weather";
        
        if (!endpoint) return;

        showPaneLoader(paneId);

        try {
            const res = await fetch(endpoint);
            if (!res.ok) throw new Error("API error fetching pane " + paneId);
            const data = await res.json();
            
            if (paneId === "hub-gov-transit-pane") {
                renderGovTransit(data);
            } else if (paneId === "hub-hdb-pane") {
                renderHdbPane(data);
            } else if (paneId === "hub-jobs-pane") {
                renderJobsPane(data);
            } else if (paneId === "hub-community-pane") {
                renderCommunityPane(data);
            } else if (paneId === "hub-env-pane") {
                renderWeatherPane(data);
            }
            
            loadedSgHubPanes[paneId] = true;
        } catch (err) {
            console.error("Failed to load pane " + paneId, err);
            showPaneError(paneId);
        }
    }

    function getRetrievalTimestamp() {
        const now = new Date();
        return now.toLocaleString("en-SG", { 
            day: 'numeric', 
            month: 'short', 
            year: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit', 
            hour12: true 
        }) + " (SGT)";
    }

    function renderWeatherPane(data) {
        const psi = data.psi || { value: 28, status: 'Good' };
        const forecasts = data.forecasts || [];

        // PSI colour thresholds
        const psiColors = {
            'Good': ['#10b981', '#d1fae5'],
            'Moderate': ['#f59e0b', '#fef3c7'],
            'Unhealthy': ['#f97316', '#ffedd5'],
            'Very Unhealthy': ['#ef4444', '#fee2e2'],
            'Hazardous': ['#991b1b', '#fca5a5']
        };
        const [psiColor, psiBg] = psiColors[psi.status] || ['#10b981', '#d1fae5'];
        const psiPct = Math.min((psi.value / 300) * 100, 100);

        // Weather condition icons
        const conditionIcon = (fc) => {
            const f = (fc || '').toLowerCase();
            if (f.includes('thunder')) return '⛈️';
            if (f.includes('shower') || f.includes('rain')) return '🌧️';
            if (f.includes('cloudy')) return '☁️';
            if (f.includes('partly')) return '⛅';
            if (f.includes('fair') || f.includes('sunny')) return '☀️';
            if (f.includes('windy')) return '💨';
            return '🌤️';
        };

        const forecastCards = forecasts.map(f => `
            <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 10px; padding: 14px 10px; text-align:center; min-width:100px; flex: 1;">
                <div style="font-size: 28px; margin-bottom: 6px;">${conditionIcon(f.forecast)}</div>
                <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">${escapeHTML(f.area)}</div>
                <div style="font-size: 12px; font-weight: 600; color: var(--text-main);">${escapeHTML(f.forecast)}</div>
            </div>
        `).join('');

        weatherContent.innerHTML = `
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 16px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
                <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${getRetrievalTimestamp()}
            </div>

            <!-- PSI Gauge Card -->
            <div style="background: ${psiBg}; border: 1px solid ${psiColor}33; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom: 12px; flex-wrap:wrap; gap:8px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: ${psiColor}; text-transform: uppercase; letter-spacing: 0.5px;">🍃 NEA Live PSI — 24-Hr National Reading</div>
                        <div style="font-size: 32px; font-weight: 800; color: ${psiColor}; line-height: 1.1; margin-top:4px;">${psi.value}</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="background: ${psiColor}; color: #fff; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 20px;">${escapeHTML(psi.status)}</span>
                        <div style="font-size: 11px; color: ${psiColor}; margin-top: 6px;">Suitable for general outdoor activity</div>
                    </div>
                </div>
                <div style="background: #fff3; border-radius: 4px; height: 8px; overflow: hidden;">
                    <div style="width: ${psiPct}%; background: ${psiColor}; height: 100%; border-radius: 4px; transition: width 0.8s ease;"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:10px; color:${psiColor}; margin-top:4px; font-weight:600;">
                    <span>0 Good</span><span>51 Moderate</span><span>101 Unhealthy</span><span>300+</span>
                </div>
            </div>

            <!-- 2-Hr Regional Forecast Cards -->
            <div style="margin-bottom: 8px;">
                <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">⛅ 2-Hour Regional Forecast</div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    ${forecastCards || '<p style="color:var(--text-subtle); margin:0;">Forecast data unavailable.</p>'}
                </div>
            </div>
        `;
    }

    function renderGovTransit(data) {
        const banner = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
            <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${getRetrievalTimestamp()}
        </div>`;
        let govHtml = "";
        data.gov_events.forEach(evt => {
            govHtml += `<div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-size: 13px; margin-bottom: 8px;">
                <div style="display:flex; justify-content:space-between; margin-bottom: 6px; font-weight:600; flex-wrap:wrap; gap:8px;">
                    <span style="color: var(--primary); display:inline-flex; align-items:center; gap:6px;">
                        <i class="fa-solid fa-bullhorn"></i> ${escapeHTML(evt.source)}
                        ${evt.date ? `<span style="font-size:10px; font-weight:normal; color:var(--text-muted); background:var(--border); padding:2px 6px; border-radius:4px;">${escapeHTML(evt.date)}</span>` : ''}
                    </span>
                    <a href="${safeURL(evt.link)}" target="_blank" style="color: var(--link); text-decoration:none;"><i class="fa-solid fa-up-right-from-square"></i> View Alert</a>
                </div>
                <div style="color: var(--text-main); line-height:1.45; white-space: pre-wrap;">${escapeHTML(evt.content)}</div>
            </div>`;
        });
        govEventsContent.innerHTML = banner + (govHtml || "<p style='color: var(--text-subtle); margin:0;'>No official alerts.</p>");

        // ── Transit section: DataMall structured view OR Telegram keyword-filter fallback ──
        let mrtHtml = "";

        if (data.train_alerts) {
            // ── LTA DataMall: structured per-line MRT status dashboard ──
            const ta = data.train_alerts;
            const overallNormal = ta.status === "Normal";
            const apiTimestamp = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display:flex; align-items:center; gap:6px; font-weight:600;">
                <i class="fa-solid fa-satellite-dish" style="color:#005EC4;"></i>
                <span>LTA DataMall Live Feed</span>
                <span style="font-size:10px; font-weight:normal; color:var(--text-muted); background:var(--border); padding:2px 7px; border-radius:4px;">Retrieved: ${escapeHTML(ta.retrieved_at)}</span>
            </div>`;

            if (overallNormal) {
                mrtHtml += `<div style="display:flex; align-items:center; gap:8px; color: #1a7f3c; background: #eafaf1; border: 1px solid #a3d9b1; padding:14px 16px; border-radius:10px; font-size:14px; font-weight:700; margin-bottom:14px;">
                    <i class="fa-solid fa-circle-check" style="font-size:18px;"></i>
                    🟢 All MRT & LRT Lines Operating Normally
                </div>`;
            } else {
                mrtHtml += `<div style="display:flex; align-items:center; gap:8px; color: #c0392b; background: #fdecea; border: 1px solid #e8b4b1; padding:14px 16px; border-radius:10px; font-size:14px; font-weight:700; margin-bottom:14px;">
                    <i class="fa-solid fa-triangle-exclamation" style="font-size:18px;"></i>
                    ⚠️ Train Service Disruptions / Minor Delays Active
                </div>`;
            }

            // Display general alert messages if present
            if (ta.messages && ta.messages.length > 0) {
                mrtHtml += `<div style="margin-bottom:16px;">`;
                ta.messages.forEach(msg => {
                    mrtHtml += `<div style="background:#fffbeb; border:1px solid #fef3c7; border-left:4px solid #d97706; border-radius:8px; padding:12px; font-size:13px; margin-bottom:8px; line-height:1.5; color:#92400e;">
                        <div style="font-weight:700; margin-bottom:4px; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#b45309;">
                            <i class="fa-solid fa-bullhorn"></i> Official Advisory (${escapeHTML(msg.created_date)})
                        </div>
                        <div>${escapeHTML(msg.content)}</div>
                    </div>`;
                });
                mrtHtml += `</div>`;
            }

            // Per-line status grid
            mrtHtml += `<div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap:10px; margin-bottom:16px;">`;
            ta.lines.forEach(line => {
                const isDisrupted = line.status === "Disrupted";
                const statusColor   = isDisrupted ? "#c0392b" : "#1a7f3c";
                const statusBg      = isDisrupted ? "#fdecea" : "#eafaf1";
                const statusBorder  = isDisrupted ? "#e8b4b1" : "#a3d9b1";
                const statusIcon    = isDisrupted ? "🔴" : "🟢";
                mrtHtml += `<div style="background:${statusBg}; border:1px solid ${statusBorder}; border-radius:8px; padding:10px 12px;">
                    <div style="display:flex; align-items:center; gap:7px; margin-bottom:4px;">
                        <span style="background:${escapeHTML(line.line_color)}; color:#fff; font-size:10px; font-weight:800; padding:2px 7px; border-radius:4px; letter-spacing:0.5px;">${escapeHTML(line.line_code)}</span>
                        <span style="font-size:12px; font-weight:700; color:${statusColor};">${statusIcon} ${isDisrupted ? "Affected" : "Normal"}</span>
                    </div>
                    <div style="font-size:11px; color:var(--text-muted);">${escapeHTML(line.line_name)}</div>
                </div>`;
            });
            mrtHtml += `</div>`;

            // Disruption detail cards (using exact LTA guide parameters)
            const disruptedLines = ta.lines.filter(l => l.status === "Disrupted");
            if (disruptedLines.length > 0) {
                mrtHtml += `<div style="font-size:12px; font-weight:700; color:var(--text-muted); margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">Disruption Scope</div>`;
                disruptedLines.forEach(line => {
                    line.affected_segments.forEach(seg => {
                        mrtHtml += `<div style="background:var(--bg-muted); border:1px solid #e8b4b1; border-left: 4px solid ${escapeHTML(line.line_color)}; border-radius:8px; padding:12px; font-size:13px; margin-bottom:8px; line-height:1.5;">
                            <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px; font-weight:700;">
                                <span style="background:${escapeHTML(line.line_color)}; color:#fff; font-size:10px; font-weight:800; padding:2px 8px; border-radius:4px;">${escapeHTML(line.line_code)}</span>
                                <span style="color:#c0392b;">${escapeHTML(line.line_name)}</span>
                                ${seg.direction ? `<span style="font-size:11px; color:var(--text-muted);">• Direction: ${escapeHTML(seg.direction)}</span>` : ''}
                            </div>
                            ${seg.stations ? `<div style="font-size:12px; color:var(--text-main); margin-bottom:6px; font-weight:600;"><i class="fa-solid fa-location-dot" style="color:var(--text-muted);"></i> Affected Stations: <span style="color:#c0392b;">${escapeHTML(seg.stations)}</span></div>` : ''}
                            
                            ${seg.free_public_bus ? `<div style="font-size:12px; color:#1a7f3c; margin-bottom:4px; font-weight:600;"><i class="fa-solid fa-bus"></i> Free Public Bus Boarding: <span>${escapeHTML(seg.free_public_bus)}</span></div>` : ''}
                            ${seg.free_mrt_shuttle ? `<div style="font-size:12px; color:#005EC4; margin-bottom:4px; font-weight:600;"><i class="fa-solid fa-bus-simple"></i> Free MRT Shuttle: <span>${escapeHTML(seg.free_mrt_shuttle)}</span> (${escapeHTML(seg.mrt_shuttle_direction)})</div>` : ''}
                        </div>`;
                    });
                });
            }

            mrtEventsContent.innerHTML = apiTimestamp + mrtHtml;

        } else {
            // ── Fallback: keyword-filter Telegram posts (no DataMall key) ──
            const transitKeywords = ["mrt", "lrt", "train", "track fault", "service delay", "smrt", "sbs transit", "lta", "road closure", "traffic accident", "delay", "disruption", "service recovery"];
            let transitEvents = [];
            data.gov_events.forEach(evt => {
                const textLower = evt.content.toLowerCase();
                const matched = transitKeywords.some(kw => textLower.includes(kw));
                if (matched && !transitEvents.some(te => te.content === evt.content)) {
                    transitEvents.push(evt);
                }
            });
            transitEvents.forEach(evt => {
                mrtHtml += `<div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-size: 13px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 6px; font-weight:600; flex-wrap:wrap; gap:8px;">
                        <span style="color: var(--primary); display:inline-flex; align-items:center; gap:6px;">
                            <i class="fa-solid fa-train-subway"></i> ${escapeHTML(evt.source)}
                            ${evt.date ? `<span style="font-size:10px; font-weight:normal; color:var(--text-muted); background:var(--border); padding:2px 6px; border-radius:4px;">${escapeHTML(evt.date)}</span>` : ''}
                        </span>
                        <a href="${safeURL(evt.link)}" target="_blank" style="color: var(--link); text-decoration:none;"><i class="fa-solid fa-up-right-from-square"></i> View Alert</a>
                    </div>
                    <div style="color: var(--text-main); line-height:1.45;">${escapeHTML(evt.content)}</div>
                </div>`;
            });
            mrtEventsContent.innerHTML = banner + (mrtHtml || `
                <div style="display:flex; align-items:center; gap:8px; color: var(--text-success); background: var(--bg-muted); border: 1px solid var(--border); padding:16px; border-radius:8px; font-size:14px; font-weight:600;">
                    <i class="fa-solid fa-circle-check" style="font-size:18px;"></i>
                    🟢 All train services are operating normally. No active disruptions reported.
                </div>`);
        }
    }

    function renderCommunityPane(data) {
        const banner = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
            <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${getRetrievalTimestamp()}
        </div>`;
        let commHtml = "";
        data.community_events.forEach(evt => {
            commHtml += `<div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-size: 13px; margin-bottom: 8px;">
                <div style="display:flex; justify-content:space-between; margin-bottom: 6px; font-weight:600; flex-wrap:wrap; gap:8px;">
                    <span style="color: var(--link); display:inline-flex; align-items:center; gap:6px;">
                        <i class="fa-solid fa-tags"></i> ${escapeHTML(evt.source)}
                        ${evt.date ? `<span style="font-size:10px; font-weight:normal; color:var(--text-muted); background:var(--border); padding:2px 6px; border-radius:4px;">${escapeHTML(evt.date)}</span>` : ''}
                    </span>
                    <a href="${safeURL(evt.link)}" target="_blank" style="color: var(--link); text-decoration:none;"><i class="fa-solid fa-up-right-from-square"></i> View Post</a>
                </div>
                <div style="color: var(--text-main); line-height:1.45;">${escapeHTML(evt.content)}</div>
            </div>`;
        });
        communityEventsContent.innerHTML = banner + (commHtml || "<p style='color: var(--text-subtle); margin:0;'>No community updates.</p>");
    }

    function renderHdbPane(data) {
        const banner = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
            <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${getRetrievalTimestamp()}
        </div>`;
        hdbLaunchesContent.innerHTML = banner + renderHdbLaunches(data.hdb);

        let hdbNewsHtml = "";
        data.hdb_news.forEach(news => {
            hdbNewsHtml += `<div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-size: 13px; margin-bottom: 8px;">
                <div style="display:flex; justify-content:space-between; margin-bottom: 6px; font-weight:600;">
                    <span style="color: var(--primary); font-size: 11px;"><i class="fa-solid fa-calendar-day"></i> ${escapeHTML(news.date)}</span>
                    <a href="${safeURL(news.link)}" target="_blank" style="color: var(--link); text-decoration:none; font-size: 11px;"><i class="fa-solid fa-up-right-from-square"></i> Read Press Release</a>
                </div>
                <div style="color: var(--text-main); line-height:1.45; font-weight:600;">${escapeHTML(news.title)}</div>
            </div>`;
        });
        hdbNewsContent.innerHTML = banner + (hdbNewsHtml || "<p style='color: var(--text-subtle); margin:0;'>No active news releases.</p>");
    }

    function renderJobsPane(data) {
        sgHubJobsData = data.jobs;
        renderSectorDetails("tech"); // Default to Tech
        renderRetrenchmentPane(data.retrenchment);
    }

    function renderRetrenchmentPane(retrenchment) {
        const headlineEl = document.getElementById("retrenchment-headline");
        const detailsEl = document.getElementById("retrenchment-details");
        const sourceEl = document.getElementById("retrenchment-source");
        if (!retrenchment || !headlineEl) return;

        // headline looks like "3,590 workers (2025-Q4)" — split the count from the quarter label
        const match = retrenchment.headline.match(/^(.*?)\s*\(([^)]+)\)\s*$/);
        const workerCount = match ? match[1] : retrenchment.headline;
        const quarterRaw = match ? match[2] : "";
        const quarterLabel = quarterRaw.includes("-")
            ? `${quarterRaw.split("-")[1]} ${quarterRaw.split("-")[0]}`
            : quarterRaw;

        headlineEl.textContent = workerCount;
        detailsEl.textContent = `Primarily in ${retrenchment.industries}. Overall six-month re-employment rate stands at ${retrenchment.reemployment_rate}.`;
        sourceEl.innerHTML = `<i class="fa-regular fa-calendar"></i> Data as of: ${escapeHTML(quarterLabel)}`;
    }

    function renderHdbLaunches(text) {
        if (!text) return "<p style='color: var(--text-subtle); margin:0;'>No launches listed.</p>";
        let html = "";
        const blocks = text.split("🏢");
        blocks.forEach(block => {
            if (!block.trim()) return;
            const lines = block.split("\n");
            const titleLine = lines[0].trim();
            if (titleLine.includes("HDB BTO LAUNCH REGISTRY") || titleLine.includes("CPF HOUSING GRANTS")) return; // skip header and grant block in text
            
            let loc = "N/A";
            let units = "N/A";
            let pricing = "N/A";
            let launchDate = "";
            lines.forEach(line => {
                const clean = line.replace(/^\s*•\s*/, '').trim();
                if (clean.includes("Location:")) loc = clean.split("Location:")[1].trim();
                else if (clean.includes("Units:")) units = clean.split("Units:")[1].trim();
                else if (clean.includes("LaunchDate:")) launchDate = clean.split("LaunchDate:")[1].trim();
                else if (clean.includes("Pricing:")) pricing = clean.split("Pricing:")[1].trim();
            });
            
            const cleanTitle = titleLine.split('(')[0].trim();

            // Category classification
            let categoryBadge = "";
            if (titleLine.includes("Prime Location Housing")) {
                categoryBadge = `<span style="background: #fdf2f2; color: #9b1c1c; border: 1px solid #f8b4b4; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase;">Prime (PLH)</span>`;
            } else if (titleLine.includes("Plus Housing")) {
                categoryBadge = `<span style="background: #e1effe; color: #1e429f; border: 1px solid #a4cafe; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase;">Plus</span>`;
            } else {
                categoryBadge = `<span style="background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase;">Standard</span>`;
            }

            const dateBadge = launchDate ? `<span style="display:inline-flex; align-items:center; gap:4px; font-size:11px; background: var(--bg-muted); border:1px solid var(--border); color:var(--text-muted); padding: 3px 8px; border-radius:12px; font-weight:600;"><i class='fa-regular fa-calendar'></i> ${escapeHTML(launchDate)}</span>` : '';

            html += `
            <div style="background: #ffffff; border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin-bottom: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02); display: flex; flex-direction: column; gap: 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; border-bottom: 1px solid var(--border); padding-bottom:10px;">
                    <strong style="color: var(--text-main); font-size:16px; font-weight:700; display:flex; align-items:center; gap:6px; margin:0;">
                        🏢 ${escapeHTML(cleanTitle)}
                    </strong>
                    <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">${dateBadge}${categoryBadge}</div>
                </div>
                <div style="font-size:13px; line-height: 1.6; color: var(--text-main); display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:12px;">
                    <div>
                        <span style="color:var(--text-muted); font-weight:600; display:block; font-size:11px; text-transform:uppercase;">📍 Town/Location</span>
                        <span style="font-size:13px; font-weight:600; color:var(--text-main);">${escapeHTML(loc)}</span>
                    </div>
                    <div>
                        <span style="color:var(--text-muted); font-weight:600; display:block; font-size:11px; text-transform:uppercase;">📊 Project Supply</span>
                        <span style="font-size:13px; font-weight:600; color:var(--text-main);">${escapeHTML(units)} units</span>
                    </div>
                    <div style="grid-column: span 2;">
                        <span style="color:var(--text-muted); font-weight:600; display:block; font-size:11px; text-transform:uppercase;">💵 Price Guidelines</span>
                        <span style="font-size:13px; font-weight:700; color:var(--text-success);">${escapeHTML(pricing)}</span>
                    </div>
                </div>
            </div>`;
        });
        return html;
    }

    function renderSectorDetails(sector) {
        if (!sgHubJobsData || !sgHubJobsData[sector]) return;
        const details = sgHubJobsData[sector];
        
        const vacNum = parseInt(details.vacancies.replace(/[^0-9]/g, '')) || 0;
        const salNum = parseInt(details.salary.replace(/[^0-9]/g, '')) || 0;
        
        const vacPct = Math.min((vacNum / 30000) * 100, 100);
        const salPct = Math.min((salNum / 12000) * 100, 100);

        // Real YoY trend + forecast come from the backend (MOM job vacancy data via data.gov.sg).
        // Risk level / drivers / support schemes below are illustrative context, not sourced from that dataset.
        const trendPctNum = parseFloat(details.trend_pct) || 0;
        const growthRate = details.trend_pct !== "N/A"
            ? `${trendPctNum >= 0 ? "▲" : "▼"} ${details.trend_pct} YoY`
            : "N/A";
        const growthColor = trendPctNum >= 0 ? "#10b981" : "#f59e0b"; // green if growing, amber if declining — matches the real trend sign

        let riskLevel = "";
        let riskColor = "";
        let growthDrivers = "";
        let momSupport = "";

        if (sector === "tech") {
            riskLevel = "Moderate (210 cases last Q)";
            riskColor = "#f59e0b";
            growthDrivers = "Generative AI applications, Cloud Infrastructure scaling, Cyber Security defense.";
            momSupport = "Eligible for TechSkills Accelerator (TeSA) training subsidies and SCTP transition programs.";
        } else if (sector === "finance") {
            riskLevel = "Low (90 cases last Q)";
            riskColor = "#10b981";
            growthDrivers = "Sustainable ESG Finance, Wealth Management setups, Blockchain asset tokenization.";
            momSupport = "Supported by IBF Standards Training and Financial Sector Technology (FSTI) grants.";
        } else if (sector === "healthcare") {
            riskLevel = "Very Low (12 cases last Q)";
            riskColor = "#10b981";
            growthDrivers = "Geriatric care expansion, National Electronic Health Records (NEHR) digitization, Telehealth platforms.";
            momSupport = "Eligible for Healthcare Professional Conversion Programmes (PCP) with up to 90% salary support.";
        } else {
            riskLevel = "Low-Moderate";
            riskColor = "#f59e0b";
            growthDrivers = "Green economy transition, advanced manufacturing automation, wholesale trade digitization.";
            momSupport = "General SCTP conversion courses and SGUnited Skills transition frameworks.";
        }

        jobsContent.innerHTML = `
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
                <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${getRetrievalTimestamp()}
            </div>
            <div style="margin-bottom: 16px;">
                <div style="display:flex; justify-content:space-between; margin-bottom: 6px; font-size:13px;">
                    <strong>📊 Active Vacancies:</strong>
                    <span style="color:var(--text-main); font-weight:700;">${escapeHTML(details.vacancies)}</span>
                </div>
                <div style="width:100%; background:var(--border); height:8px; border-radius:4px; overflow:hidden;">
                    <div style="width:${vacPct}%; background:linear-gradient(90deg, var(--primary) 0%, #ff8882 100%); height:100%; border-radius:4px;"></div>
                </div>
            </div>
            
            <div style="margin-bottom: 16px;">
                <div style="display:flex; justify-content:space-between; margin-bottom: 6px; font-size:13px;">
                    <strong>💵 Median Starting Salary:</strong>
                    <span style="color:var(--link); font-weight:700;">${escapeHTML(details.salary)}</span>
                </div>
                <div style="width:100%; background:var(--border); height:8px; border-radius:4px; overflow:hidden;">
                    <div style="width:${salPct}%; background:linear-gradient(90deg, var(--link) 0%, #8bc4ff 100%); height:100%; border-radius:4px;"></div>
                </div>
            </div>

            <div style="margin-bottom: 16px; font-size:13px;">
                <span style="display:block; margin-bottom:6px; color: var(--text-muted); font-weight:700;">🔑 Top Demanded Skills:</span>
                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                    ${details.skills.split(",").map(sk => `<span style="background: var(--primary-soft); color: var(--primary); border:1px solid var(--border); border-radius:12px; padding:2px 10px; font-size:11px; font-weight:600;">${escapeHTML(sk.trim())}</span>`).join("")}
                </div>
            </div>
            
            <div style="border-top: 1px solid var(--border); padding-top: 12px; margin-top: 12px; font-size:12px; color: var(--text-muted); line-height:1.5;">
                <strong>📈 Industry Outlook:</strong> ${escapeHTML(details.trend)}
            </div>

            <div style="margin-top: 16px; border-top: 1px solid var(--border); padding-top: 16px;">
                <strong style="display:block; margin-bottom:10px; font-size:13px; color:var(--text-main); font-weight:700;">
                    <i class="fa-solid fa-chart-pie" style="color:var(--primary);"></i> YA 2026 MOM Sector Insights
                </strong>
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-bottom: 12px;">
                    <div style="background: var(--bg-muted); border: 1px solid var(--border); padding: 10px; border-radius: 6px;">
                        <span style="font-size: 10px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 4px; text-transform: uppercase;">📈 YoY Growth Index</span>
                        <strong style="font-size: 14px; color: ${growthColor};">${growthRate}</strong>
                    </div>
                    <div style="background: var(--bg-muted); border: 1px solid var(--border); padding: 10px; border-radius: 6px;">
                        <span style="font-size: 10px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 4px; text-transform: uppercase;">⚠️ Retrenchment Risk</span>
                        <strong style="font-size: 13px; color: ${riskColor};">${riskLevel}</strong>
                    </div>
                </div>
                <div style="font-size:12px; line-height: 1.5; color: var(--text-main); margin-bottom:8px;">
                    <strong>💡 Market Drivers:</strong> ${escapeHTML(growthDrivers)}
                </div>
                <div style="font-size:12px; line-height: 1.5; color: var(--text-main);">
                    <strong>🎯 Support Scheme:</strong> ${escapeHTML(momSupport)}
                </div>
            </div>

            <div style="margin-top: 16px; border-top: 1px solid var(--border); padding-top: 12px; display:flex; justify-content:flex-end;">
                <button class="chat-sector-btn" data-prompt="Analyze the YA 2026 job market trends, salaries and active vacancies in Singapore's ${sector} sector" style="background:var(--primary); color:#ffffff; font-weight:700; border:none; padding:8px 14px; border-radius:6px; font-size:12px; cursor:pointer; transition:all 0.2s ease;">
                    <i class="fa-solid fa-robot"></i> Ask Co-Pilot to Analyze
                </button>
            </div>
        `;

        const chatSectorBtn = jobsContent.querySelector(".chat-sector-btn");
        if (chatSectorBtn) {
            chatSectorBtn.addEventListener("click", () => {
                const prompt = chatSectorBtn.getAttribute("data-prompt");
                const portalsBtn = document.getElementById("main-tab-portals-btn");
                if (portalsBtn) portalsBtn.click();
                
                const widget = document.getElementById("chat-widget");
                const trigger = document.getElementById("chat-trigger");
                if (widget && widget.classList.contains("hidden")) {
                    if (trigger) trigger.click();
                }
                
                const input = document.getElementById("user-input");
                if (input) {
                    input.value = prompt;
                    const form = document.getElementById("chat-form");
                    if (form) {
                        setTimeout(() => {
                            form.dispatchEvent(new Event("submit"));
                        }, 300);
                    }
                }
            });
        }
    }

    // Toggle Hub loading on main tab click
    if (mainTabHubBtn) {
        mainTabHubBtn.addEventListener("click", () => {
            const activeSubTab = document.querySelector(".hub-sub-tab-btn.active-hub-sub-tab");
            if (activeSubTab) {
                const targetPaneId = activeSubTab.getAttribute("data-hub-sub-tab");
                loadSgHubPaneData(targetPaneId);
            } else {
                loadSgHubPaneData("hub-gov-transit-pane");
            }
        });
    }

    async function loadJobSectorData(sector) {
        if (sgHubJobsData && sgHubJobsData[sector]) {
            renderSectorDetails(sector);
            return;
        }
        
        jobsContent.innerHTML = `<p style='color: var(--text-subtle); margin:0;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading ${sector} sector statistics...</p>`;
        
        try {
            const res = await fetch(`/api/sg-hub/jobs?sector=${sector}`);
            if (!res.ok) throw new Error("API error fetching job sector " + sector);
            const data = await res.json();
            
            if (!sgHubJobsData) sgHubJobsData = {};
            sgHubJobsData[sector] = data.jobs[sector];
            
            renderSectorDetails(sector);
        } catch (err) {
            console.error("Failed to load sector " + sector, err);
            jobsContent.innerHTML = `<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load ${sector} statistics.</p>`;
        }
    }

    // Job Sector switcher click handling
    sectorTabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            sectorTabButtons.forEach(b => {
                b.classList.remove("active-sector");
            });
            btn.classList.add("active-sector");
            
            const sector = btn.getAttribute("data-sector");
            loadJobSectorData(sector);
        });
    });
}

// Initialize SG Hub features on load
document.addEventListener("DOMContentLoaded", () => {
    initSgHub();
});
