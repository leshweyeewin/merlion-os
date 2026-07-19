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
    initPortalVisibility();

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
        const cards = container.querySelectorAll(".service-card:not(.dragging):not(.portal-hidden)");
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

// Lets users hide portal cards they don't use (the directory has grown to 39 entries) and
// bring them back on demand via the "Hidden Portals" dropdown, persisted in localStorage.
function initPortalVisibility() {
    const STORAGE_KEY = "merlionos-hidden-portals";
    const grid = document.querySelector(".grid-container");
    const manageBtn = document.getElementById("manage-portals-btn");
    const dropdown = document.getElementById("hidden-portals-dropdown");
    const countBadge = document.getElementById("hidden-portals-count");
    if (!grid) return;

    function loadHidden() {
        try {
            const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
            return Array.isArray(saved) ? saved : [];
        } catch (e) {
            return [];
        }
    }

    function saveHidden(list) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    }

    function cardName(card) {
        const nameEl = card.querySelector("h3");
        return nameEl ? nameEl.textContent.trim() : card.dataset.agency;
    }

    function updateBadge() {
        const hidden = loadHidden();
        if (hidden.length > 0) {
            countBadge.textContent = hidden.length;
            countBadge.style.display = "inline-block";
        } else {
            countBadge.style.display = "none";
        }
    }

    function renderDropdown() {
        const hidden = loadHidden();
        if (hidden.length === 0) {
            dropdown.innerHTML = `<div class="hidden-portals-empty">No portals hidden — hover any card and click the eye icon to hide it.</div>`;
            return;
        }
        const cardsByAgency = new Map(Array.from(grid.querySelectorAll(".service-card")).map(c => [c.dataset.agency, c]));
        dropdown.innerHTML = hidden.map(agency => {
            const card = cardsByAgency.get(agency);
            const name = card ? cardName(card) : agency;
            return `<div class="hidden-portal-chip">
                <span class="hidden-portal-chip-name">${escapeHTML(name)}</span>
                <button type="button" class="add-portal-back-btn" data-agency="${escapeHTML(agency)}">+ Add back</button>
            </div>`;
        }).join('');
    }

    function hidePortal(agency) {
        const hidden = loadHidden();
        if (!hidden.includes(agency)) {
            hidden.push(agency);
            saveHidden(hidden);
        }
        const card = grid.querySelector(`.service-card[data-agency="${agency}"]`);
        if (card) card.classList.add("portal-hidden");
        updateBadge();
        renderDropdown();
    }

    function showPortal(agency) {
        saveHidden(loadHidden().filter(a => a !== agency));
        const card = grid.querySelector(`.service-card[data-agency="${agency}"]`);
        if (card) card.classList.remove("portal-hidden");
        updateBadge();
        renderDropdown();
    }

    grid.querySelectorAll(".service-card").forEach(card => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "hide-portal-btn";
        btn.title = "Hide this portal";
        btn.innerHTML = `<i class="fa-solid fa-eye-slash"></i>`;
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            hidePortal(card.dataset.agency);
        });
        card.appendChild(btn);
    });

    loadHidden().forEach(agency => {
        const card = grid.querySelector(`.service-card[data-agency="${agency}"]`);
        if (card) card.classList.add("portal-hidden");
    });
    updateBadge();

    if (manageBtn && dropdown) {
        manageBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const willOpen = dropdown.classList.contains("hidden");
            if (willOpen) renderDropdown();
            dropdown.classList.toggle("hidden", !willOpen);
        });

        dropdown.addEventListener("click", (e) => {
            const btn = e.target.closest(".add-portal-back-btn");
            if (btn) showPortal(btn.dataset.agency);
        });

        document.addEventListener("click", (e) => {
            if (!dropdown.contains(e.target) && !manageBtn.contains(e.target)) {
                dropdown.classList.add("hidden");
            }
        });
    }
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
    const icaEventsContent = document.getElementById("hub-ica-events-content");
    const hdbLaunchesContent = document.getElementById("hub-hdb-launches");
    const hdbNewsContent = document.getElementById("hub-hdb-news");
    const hdbResaleContent = document.getElementById("hub-hdb-resale");
    const transportContent = document.getElementById("hub-transport-content");
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
        "gov-transit-group": false,
        "hub-hdb-pane": false,
        "hub-jobs-pane": false,
        "hub-community-pane": false,
        "hub-env-pane": false
    };

    function showPaneLoader(paneId) {
        if (paneId === "hub-transport-pane" || paneId === "hub-gov-transit-pane") {
            mrtEventsContent.innerHTML = "<p style='color: var(--text-subtle); margin:0;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading transit advisories...</p>";
            if (transportContent) transportContent.innerHTML = "<p style='color: var(--text-subtle); margin:0;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading transport data...</p>";
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
        if (paneId === "hub-transport-pane" || paneId === "hub-gov-transit-pane") {
            mrtEventsContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load transit feeds.</p>";
            if (transportContent) transportContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load transport data.</p>";
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

    function getBrowserLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) { reject(new Error("Geolocation not supported by this browser.")); return; }
            // No `timeout` option here deliberately — the countdown starts the moment this fires,
            // and that includes however long the user takes to notice and click the permission
            // prompt. A short timeout (e.g. 4s) races that prompt and fails before most people
            // even get to click "Allow". Let it wait as long as it takes; this is only called
            // from an explicit user click ("Around You"), never automatically on page load.
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
                (err) => reject(err),
                { maximumAge: 5 * 60 * 1000 }
            );
        });
    }

    // "Transit & Transport" and "Gov Updates" are two separate tabs but share one backend call
    // (train alerts, taxi availability, and COE are fetched in parallel with the Telegram gov
    // channels server-side) — cache and load them together under one key so switching between
    // the two tabs never triggers a redundant re-scrape.
    const GOV_TRANSIT_GROUP = ["hub-transport-pane", "hub-gov-transit-pane"];

    async function loadSgHubPaneData(paneId) {
        const cacheKey = GOV_TRANSIT_GROUP.includes(paneId) ? "gov-transit-group" : paneId;
        if (loadedSgHubPanes[cacheKey]) return;

        let endpoint = "";
        if (GOV_TRANSIT_GROUP.includes(paneId)) endpoint = "/api/sg-hub/gov-transit";
        else if (paneId === "hub-hdb-pane") endpoint = "/api/sg-hub/hdb";
        else if (paneId === "hub-jobs-pane") endpoint = "/api/sg-hub/jobs?sector=tech";
        else if (paneId === "hub-community-pane") endpoint = "/api/sg-hub/community";
        else if (paneId === "hub-env-pane") endpoint = "/api/sg-hub/weather";

        if (!endpoint) return;

        // The Occupational Wage Explorer has its own (heavier, Excel-backed) endpoint — kick it
        // off in parallel with the main jobs fetch; it caches itself under its own key.
        if (paneId === "hub-jobs-pane") loadOccupationalWages();

        showPaneLoader(paneId);

        try {
            const res = await fetch(endpoint);
            if (!res.ok) throw new Error("API error fetching pane " + paneId);
            const data = await res.json();

            if (GOV_TRANSIT_GROUP.includes(paneId)) {
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

            loadedSgHubPanes[cacheKey] = true;
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

        // Current Conditions stat tiles (temp / humidity / wind / rainfall / PM2.5)
        const cc = data.current_conditions || {};
        const statTile = (icon, label, value) => `
            <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 10px; padding: 12px 10px; text-align:center; min-width:100px; flex: 1;">
                <div style="font-size: 22px; margin-bottom: 4px;">${icon}</div>
                <div style="font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">${label}</div>
                <div style="font-size: 14px; font-weight: 700; color: var(--text-main);">${value}</div>
            </div>`;

        const rainfallLabel = (cc.rainfall_stations_total)
            ? `${cc.rainfall_max ?? 0} mm max (${cc.rainfall_stations_wet}/${cc.rainfall_stations_total} areas)`
            : 'N/A';

        // UV Index: NEA 5-tier scale
        const uvVal = cc.uv_index != null ? cc.uv_index : null;
        const uvLabel = uvVal == null ? 'N/A'
            : uvVal <= 2 ? `${uvVal} Low`
            : uvVal <= 5 ? `${uvVal} Moderate`
            : uvVal <= 7 ? `${uvVal} High`
            : uvVal <= 10 ? `${uvVal} Very High`
            : `${uvVal} Extreme`;
        const uvColor = uvVal == null ? 'var(--text-muted)'
            : uvVal <= 2 ? '#10b981'
            : uvVal <= 5 ? '#f59e0b'
            : uvVal <= 7 ? '#f97316'
            : uvVal <= 10 ? '#ef4444'
            : '#991b1b';
        const uvTile = `
            <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 10px; padding: 12px 10px; text-align:center; min-width:100px; flex: 1;">
                <div style="font-size: 22px; margin-bottom: 4px;">☀️</div>
                <div style="font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">UV Index</div>
                <div style="font-size: 14px; font-weight: 700; color: ${uvColor};">${uvLabel}</div>
            </div>`;

        const currentConditionsTiles = [
            statTile('🌡️', 'Air Temp', cc.air_temperature != null ? `${cc.air_temperature}°C` : 'N/A'),
            statTile('💧', 'Humidity', cc.humidity != null ? `${cc.humidity}%` : 'N/A'),
            statTile('💨', 'Wind', (cc.wind_speed != null && cc.wind_direction) ? `${cc.wind_speed} km/h ${cc.wind_direction}` : 'N/A'),
            statTile('🌧️', 'Rainfall', rainfallLabel),
            statTile('🍃', 'PM2.5', data.pm25 != null ? `${data.pm25} µg/m³` : 'N/A'),
            uvTile
        ].join('');

        // 24-Hour General Outlook
        const outlook = data.outlook_24hr;
        const outlookHtml = outlook ? `
            <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; margin-top: 8px;">
                <div style="font-size: 13px; font-weight: 700; color: var(--text-main); margin-bottom: 6px;">${conditionIcon(outlook.forecast)} ${escapeHTML(outlook.forecast || 'N/A')}</div>
                <div style="font-size: 12px; color: var(--text-muted); line-height: 1.6;">
                    🌡️ ${outlook.temp_low ?? '–'}–${outlook.temp_high ?? '–'}°C &nbsp;•&nbsp;
                    💧 ${outlook.humidity_low ?? '–'}–${outlook.humidity_high ?? '–'}% &nbsp;•&nbsp;
                    💨 ${outlook.wind_speed_low ?? '–'}–${outlook.wind_speed_high ?? '–'} km/h ${escapeHTML(outlook.wind_direction || '')}
                </div>
            </div>
        ` : '';

        weatherContent.innerHTML = `
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 16px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
                <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${escapeHTML(data.synced_at || getRetrievalTimestamp())}
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

            <!-- Current Conditions -->
            <div style="margin-bottom: 16px;">
                <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">🌤️ Current Conditions (NEA Station Average)</div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    ${currentConditionsTiles}
                </div>
            </div>

            <!-- 2-Hr Regional Forecast Cards -->
            <div style="margin-bottom: 8px;">
                <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">⛅ 2-Hour Regional Forecast</div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    ${forecastCards || '<p style="color:var(--text-subtle); margin:0;">Forecast data unavailable.</p>'}
                </div>
            </div>

            <!-- 24-Hour Outlook -->
            <div>
                <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">📅 24-Hour Outlook</div>
                ${outlookHtml || '<p style="color:var(--text-subtle); margin:0;">Outlook data unavailable.</p>'}
            </div>
        `;
    }

    function renderTransportPane(taxiAvailability, coe) {
        if (!transportContent) return;

        const banner = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
            <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${escapeHTML((coe && coe.synced_at) || getRetrievalTimestamp())}
        </div>`;

        const taxiHtml = !taxiAvailability
            ? `<div style="flex: 1; min-width: 180px; background: var(--bg-muted); border: 1px solid var(--border); padding: 14px; border-radius: 8px; color: var(--text-subtle); font-size: 13px;">
                🚕 Taxi availability unavailable (LTA DataMall key not configured).
            </div>`
            : `<div id="taxi-stat-block" style="flex: 1; min-width: 180px; background: var(--bg-muted); border: 1px solid var(--border); padding: 14px; border-radius: 8px;">
                ${islandwideTaxiHtml(taxiAvailability)}
            </div>`;

        const coeCategoryColors = { 'A': '#2563eb', 'B': '#7c3aed', 'C': '#d97706', 'D': '#059669', 'E': '#dc2626' };
        const coeCategoriesHtml = (coe && coe.categories && coe.categories.length)
            ? coe.categories.map(c => `
                <div style="background: var(--bg-panel); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; min-width: 130px; flex: 1;">
                    <span style="background:${coeCategoryColors[c.category] || 'var(--primary)'}; color:#fff; font-size:10px; font-weight:800; padding:2px 7px; border-radius:4px;">CAT ${escapeHTML(c.category)}</span>
                    <div style="font-size: 15px; font-weight: 700; color: var(--text-main); margin-top: 6px;">${escapeHTML(c.premium)}</div>
                    <div style="font-size: 10px; color: var(--text-muted);">${escapeHTML(c.label)}</div>
                </div>`).join('')
            : `<p style="color: var(--text-subtle); margin:0; font-size: 13px;">COE data unavailable.</p>`;

        transportContent.innerHTML = banner + `
            <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px;">
                ${taxiHtml}
                <div style="flex: 2; min-width: 220px; background: var(--bg-muted); border: 1px solid var(--border); padding: 14px; border-radius: 8px;">
                    <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 8px;">🚗 COE BIDDING — ${coe ? escapeHTML(coe.exercise) : 'N/A'}</span>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        ${coeCategoriesHtml}
                    </div>
                </div>
            </div>
        `;

        bindTaxiButtons(taxiAvailability);
    }

    const TAXI_BTN_STYLE = "background: var(--bg-panel); border: 1px solid var(--border); color: var(--text-main); padding: 5px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer; display:inline-flex; align-items:center; gap:5px;";

    function islandwideTaxiHtml(taxiAvailability) {
        return `
            <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 6px;">🚕 TAXIS AVAILABLE ISLANDWIDE</span>
            <strong style="font-size: 22px; color: var(--primary); display:block;">${taxiAvailability.count.toLocaleString()}</strong>
            <span style="font-size: 10px; color: var(--text-muted); display:block; margin-bottom:8px;">${escapeHTML(taxiAvailability.retrieved_at)}</span>
            <button type="button" id="taxi-around-you-btn" style="${TAXI_BTN_STYLE}">
                <i class="fa-solid fa-location-crosshairs"></i> Around You
            </button>
        `;
    }

    function nearbyTaxiHtml(nearby) {
        return `
            <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 6px;">🚕 TAXIS WITHIN ${nearby.nearby_radius_km}KM${nearby.area_name ? "" : " OF YOU"}</span>
            ${nearby.area_name ? `<span style="font-size: 13px; font-weight: 700; color: var(--text-main); display:block; margin-bottom: 2px;"><i class="fa-solid fa-location-dot" style="color: var(--primary);"></i> Near ${escapeHTML(nearby.area_name)}</span>` : ""}
            <strong style="font-size: 22px; color: var(--primary); display:block;">${nearby.nearby_count.toLocaleString()}</strong>
            <span style="font-size: 10px; color: var(--text-muted); display:block; margin-bottom:8px;">${nearby.count.toLocaleString()} available islandwide &middot; ${escapeHTML(nearby.retrieved_at)}</span>
            <div style="display:flex; gap:6px;">
                <button type="button" id="taxi-around-you-btn" style="${TAXI_BTN_STYLE}">
                    <i class="fa-solid fa-arrows-rotate"></i> Refresh
                </button>
                <button type="button" id="taxi-show-all-btn" style="${TAXI_BTN_STYLE}">
                    <i class="fa-solid fa-globe"></i> Show All
                </button>
            </div>
        `;
    }

    function showTaxiError(block, message) {
        if (!block) return;
        block.querySelectorAll(".taxi-around-you-error").forEach(e => e.remove());
        const errEl = document.createElement("div");
        errEl.className = "taxi-around-you-error";
        errEl.style.cssText = "font-size:10px; color: var(--text-error); margin-top:6px;";
        errEl.textContent = `⚠️ ${message}`;
        block.appendChild(errEl);
    }

    function bindTaxiButtons(taxiAvailability) {
        const block = document.getElementById("taxi-stat-block");
        const aroundBtn = document.getElementById("taxi-around-you-btn");
        const showAllBtn = document.getElementById("taxi-show-all-btn");

        if (showAllBtn) {
            showAllBtn.addEventListener("click", () => {
                if (block) block.innerHTML = islandwideTaxiHtml(taxiAvailability);
                bindTaxiButtons(taxiAvailability);
            });
        }

        if (!aroundBtn) return;
        aroundBtn.addEventListener("click", async () => {
            const originalLabel = aroundBtn.innerHTML;
            aroundBtn.disabled = true;
            aroundBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Locating...`;

            let loc;
            try {
                loc = await getBrowserLocation();
            } catch (err) {
                const reason = err && err.code === 1 ? "Location access denied."
                    : err && err.code === 3 ? "Location request timed out."
                    : "Location unavailable.";
                aroundBtn.disabled = false;
                aroundBtn.innerHTML = originalLabel;
                showTaxiError(block, reason);
                return;
            }

            try {
                const res = await fetch(`/api/sg-hub/taxi-nearby?lat=${loc.lat}&lon=${loc.lon}`);
                if (!res.ok) throw new Error("Nearby taxi lookup failed");
                const nearby = await res.json();
                if (block) block.innerHTML = nearbyTaxiHtml(nearby);
                bindTaxiButtons(taxiAvailability);
            } catch (err) {
                aroundBtn.disabled = false;
                aroundBtn.innerHTML = originalLabel;
                showTaxiError(block, "Couldn't fetch nearby taxis. Try again.");
            }
        });
    }

    function renderGovTransit(data) {
        renderTransportPane(data.taxi_availability, data.coe);

        const banner = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
            <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${getRetrievalTimestamp()}
        </div>`;

        // --- ICA Newsroom Advisories ---
        if (icaEventsContent) {
            let icaHtml = "";
            if (data.ica_news && data.ica_news.length > 0) {
                data.ica_news.forEach(news => {
                    const isAdvisory = news.category.toLowerCase().includes("advisory") || news.title.toLowerCase().includes("heavy") || news.title.toLowerCase().includes("traffic") || news.title.toLowerCase().includes("checkpoint");
                    const icon = isAdvisory ? `<i class="fa-solid fa-triangle-exclamation" style="color:#d97706;"></i>` : `<i class="fa-solid fa-newspaper" style="color:var(--primary);"></i>`;
                    const borderLeft = isAdvisory ? "4px solid #d97706" : "1px solid var(--border)";
                    const bg = isAdvisory ? "#fffbeb" : "var(--bg-muted)";
                    const labelColor = isAdvisory ? "#b45309" : "var(--text-muted)";
                    const labelBg = isAdvisory ? "#fef3c7" : "var(--border)";
                    
                    icaHtml += `<div style="background: ${bg}; border: 1px solid var(--border); border-left: ${borderLeft}; border-radius: 8px; padding: 12px; font-size: 13px; margin-bottom: 8px; display: flex; gap: 12px; align-items: flex-start;">
                        ${news.image ? `<img src="${safeURL(news.image)}" alt="ICA image" style="width: 64px; height: 64px; object-fit: cover; border-radius: 6px; flex-shrink:0; border: 1px solid var(--border);" onerror="this.style.display='none'">` : ''}
                        <div style="flex-grow:1;">
                            <div style="display:flex; justify-content:space-between; margin-bottom: 4px; font-weight:600; flex-wrap:wrap; gap:6px;">
                                <span style="display:inline-flex; align-items:center; gap:6px; font-size:11.5px; color:${labelColor};">
                                    ${icon} <span style="background:${labelBg}; padding:2px 6px; border-radius:4px; font-weight:bold; font-size:10px;">${escapeHTML(news.category)}</span>
                                    ${news.date ? `<span style="font-weight:normal; color:var(--text-muted);">${escapeHTML(news.date)}</span>` : ''}
                                </span>
                                <a href="${safeURL(news.url)}" target="_blank" style="color: var(--link); text-decoration:none; font-size:12px;"><i class="fa-solid fa-up-right-from-square"></i> View</a>
                            </div>
                            <div style="color: var(--text-main); line-height:1.4; font-weight:500;">${escapeHTML(news.title)}</div>
                        </div>
                    </div>`;
                });
            } else {
                icaHtml = `<p style="color: var(--text-subtle); margin: 0; font-style: italic;">No active checkpoint or media updates reported.</p>`;
            }
            icaEventsContent.innerHTML = banner + icaHtml;
        }

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

        // --- Flood Alerts Banner (PUB real-time API) ---
        let floodBannerHtml = '';
        if (data.flood_alerts && data.flood_alerts.alerts) {
            const fa = data.flood_alerts;
            const activeAlerts = fa.alerts.filter(a => a.is_active);
            const cancelledAlerts = fa.alerts.filter(a => !a.is_active);

            if (activeAlerts.length > 0) {
                const alertItems = activeAlerts.map(a =>
                    `<div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;">
                        <i class="fa-solid fa-triangle-exclamation" style="color:#dc2626; margin-top:2px; flex-shrink:0;"></i>
                        <span>${escapeHTML(a.message)}</span>
                    </div>`
                ).join('');
                floodBannerHtml = `
                    <div style="background:#fef2f2; border:1px solid #fca5a5; border-left:4px solid #dc2626; border-radius:10px; padding:14px 16px; margin-bottom:12px;">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px; font-weight:700; font-size:13px; color:#dc2626;">
                            <i class="fa-solid fa-droplet" style="font-size:16px;"></i>
                            ⚠️ PUB Flood Alert${activeAlerts.length > 1 ? 's' : ''} Active (${activeAlerts.length})
                            ${fa.retrieved_at ? `<span style="font-size:10px; font-weight:normal; color:#b91c1c; background:#fee2e2; padding:2px 7px; border-radius:4px; margin-left:4px;">Retrieved: ${escapeHTML(fa.retrieved_at)}</span>` : ''}
                        </div>
                        <div style="font-size:13px; color:#7f1d1d; line-height:1.5;">${alertItems}</div>
                    </div>`;
            } else if (cancelledAlerts.length > 0) {
                floodBannerHtml = `
                    <div style="background:var(--bg-muted); border:1px solid var(--border); border-left:4px solid #10b981; border-radius:10px; padding:12px 16px; margin-bottom:12px; font-size:12px; color:var(--text-muted); display:flex; align-items:center; gap:8px;">
                        <i class="fa-solid fa-circle-check" style="color:#10b981;"></i>
                        <span>All earlier PUB flood alerts have been cleared.</span>
                    </div>`;
            } else {
                floodBannerHtml = `
                    <div style="background:var(--bg-muted); border:1px solid var(--border); border-left:4px solid #3b82f6; border-radius:10px; padding:10px 14px; margin-bottom:12px; font-size:11.5px; color:var(--text-muted); display:flex; align-items:center; justify-content:space-between; gap:8px;">
                        <div style="display:flex; align-items:center; gap:6px;">
                            <i class="fa-solid fa-circle-info" style="color:#3b82f6;"></i>
                            <span>No active flood alerts islandwide (PUB).</span>
                        </div>
                        ${fa.retrieved_at ? `<span style="font-size:9.5px; color:var(--text-muted);">Checked: ${escapeHTML(fa.retrieved_at)}</span>` : ''}
                    </div>`;
            }
        }

        govEventsContent.innerHTML = banner + floodBannerHtml + (govHtml || "<p style='color: var(--text-subtle); margin:0;'>No official alerts.</p>");

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

        renderHdbResalePane(data.resale);
    }

    function renderHdbResalePane(resale) {
        if (!resale || !hdbResaleContent) return;

        const yoyColor = resale.yoy_pct == null ? 'var(--text-muted)' : (resale.yoy_pct >= 0 ? '#c0392b' : '#1a7f3c');
        const yoyIcon = resale.yoy_pct == null ? '' : (resale.yoy_pct >= 0 ? '📈' : '📉');
        const yoyText = resale.yoy_pct == null ? ''
            : `${resale.yoy_pct >= 0 ? '+' : ''}${resale.yoy_pct.toFixed(1)}% (vs S$${resale.prior_median_price.toLocaleString()} in ${escapeHTML(resale.prior_month)})`;

        const banner = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
            <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${escapeHTML(resale.synced_at || getRetrievalTimestamp())}
        </div>`;

        const towns = resale.towns || [];
        const maxPrice = Math.max(...towns.map(t => t.median_price), 1);
        const townRows = towns.map(t => `
            <div style="display:flex; align-items:center; gap:10px; padding: 6px 0; border-bottom: 1px solid var(--border);">
                <div style="flex: 1; min-width:0; font-size:13px; font-weight:600; color: var(--text-main); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHTML(t.town)}</div>
                <div style="width:100px; flex-shrink:0;">
                    <div style="background: var(--bg-panel); border-radius:4px; height:7px; overflow:hidden;">
                        <div style="width:${(t.median_price / maxPrice) * 100}%; background: var(--primary); height:100%; border-radius:4px;"></div>
                    </div>
                </div>
                <div style="width:90px; flex-shrink:0; text-align:right; font-size:13px; font-weight:700; color: var(--text-main);">S$${t.median_price.toLocaleString()}</div>
                <div style="width:60px; flex-shrink:0; text-align:right; font-size:10px; color: var(--text-muted);">${t.transaction_count.toLocaleString()} txns</div>
            </div>
        `).join('');

        hdbResaleContent.innerHTML = banner + `
            <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 14px;">
                <div style="flex: 1; min-width: 200px; background: var(--bg-muted); border: 1px solid var(--border); padding: 14px; border-radius: 8px;">
                    <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 6px;">📊 ISLANDWIDE MEDIAN (${escapeHTML(resale.latest_month)})</span>
                    <strong style="font-size: 20px; color: var(--primary); display:block;">S$${resale.median_price.toLocaleString()}</strong>
                    ${yoyText ? `<span style="font-size: 12px; font-weight: 700; color: ${yoyColor};">${yoyIcon} ${escapeHTML(yoyText)} YoY</span>` : ''}
                </div>
                <div style="flex: 1; min-width: 200px; background: var(--bg-muted); border: 1px solid var(--border); padding: 14px; border-radius: 8px;">
                    <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 6px;">🏙️ PRICIEST TOWN</span>
                    ${towns.length ? `<strong style="font-size: 16px; color: var(--text-main); display:block;">${escapeHTML(towns[0].town)}</strong><span style="font-size:12px; color: var(--text-muted);">S$${towns[0].median_price.toLocaleString()} median</span>` : '<span style="color:var(--text-subtle);">N/A</span>'}
                </div>
            </div>

            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">🗺️ Median Resale Price by Town</div>
            <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 10px 16px; max-height: 340px; overflow-y: auto;">
                ${townRows || '<p style="color: var(--text-subtle); margin:0;">No town-level data available.</p>'}
            </div>
            <div style="font-size: 10px; color: var(--text-muted); margin-top: 10px;">💡 Source: ${escapeHTML(resale.source)}</div>
        `;
    }

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
        xLabels.forEach((lab, i) => {
            if (i % xTickEvery !== 0 && i !== xLabels.length - 1) return;
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
    }
    // ==== end chart layer =======================================================

    function renderJobHistoryCharts(history) {
        const vtEl = document.getElementById("hub-vacancy-trend");
        if (vtEl && history && history.vacancy && history.vacancy.years.length > 1) {
            const v = history.vacancy;
            const latestI = v.years.length - 1;
            const seriesDefs = [
                { name: "Tech", color: CHART_SERIES[0], values: v.sectors.tech },
                { name: "Finance", color: CHART_SERIES[1], values: v.sectors.finance },
                { name: "Healthcare", color: CHART_SERIES[2], values: v.sectors.healthcare },
            ];
            const leader = seriesDefs.slice().sort((a, b) => b.values[latestI] - a.values[latestI])[0];
            vtEl.innerHTML = `
                <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin: 16px 0 8px;">📈 Vacancy Trend by Sector (${escapeHTML(v.years[0])}–${escapeHTML(v.years[latestI])})</div>
                <div id="vacancy-trend-chart" style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 10px 10px 4px;"></div>
                <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;">💡 ${escapeHTML(leader.name)} leads with ${leader.values[latestI].toLocaleString()} open roles in ${escapeHTML(v.years[latestI])}. Hover for exact counts per year. Source: MOM Job Vacancy by Industry &amp; Occupation.</div>`;
            renderLineChart(document.getElementById("vacancy-trend-chart"), { xLabels: v.years, series: seriesDefs });
        }

        const rtEl = document.getElementById("hub-retrenchment-trend");
        if (rtEl && history && history.retrenchment && history.retrenchment.quarters.length > 1) {
            const r = history.retrenchment;
            const labels = r.quarters.map(q => { const [yy, qq] = q.split("-"); return `${qq} '${yy.slice(-2)}`; });
            const latest = r.totals[r.totals.length - 1];
            const prior4 = r.totals.slice(-5, -1);
            const avg4 = prior4.length ? prior4.reduce((a, b) => a + b, 0) / prior4.length : latest;
            const delta = avg4 ? ((latest - avg4) / avg4) * 100 : 0;
            rtEl.innerHTML = `
                <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin: 16px 0 8px;">📉 Quarterly Retrenchments — Last ${r.quarters.length} Quarters</div>
                <div id="retrenchment-trend-chart" style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 10px 10px 4px;"></div>
                <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;">💡 Latest quarter (${latest.toLocaleString()} workers) is ${Math.abs(delta) < 1 ? 'in line with' : `<strong style="color:${delta < 0 ? '#1a7f3c' : '#c0392b'};">${delta > 0 ? '+' : ''}${delta.toFixed(0)}%</strong> vs`} the average of the four quarters before it. Hover for exact headcounts.</div>`;
            renderLineChart(document.getElementById("retrenchment-trend-chart"), {
                xLabels: labels,
                series: [{ name: "Retrenched", color: CHART_SERIES[0], values: r.totals }],
                xTickEvery: 4,
                endLabels: false,
            });
        }
    }

    function renderJobsPane(data) {
        sgHubJobsData = data.jobs;
        renderSectorDetails("tech"); // Default to Tech
        renderRetrenchmentPane(data.retrenchment);
        renderJobHistoryCharts(data.history);
    }

    let occWagesData = null;

    async function loadOccupationalWages() {
        if (loadedSgHubPanes["hub-occ-wages"]) return;
        const container = document.getElementById("hub-occ-wages-content");
        if (!container) return;
        container.innerHTML = "<p style='color: var(--text-subtle); margin:0; font-style: italic;'><i class='fa-solid fa-circle-notch fa-spin'></i> Loading MOM occupational wage tables (500+ job titles)...</p>";
        try {
            const res = await fetch("/api/sg-hub/wages");
            if (!res.ok) throw new Error("API error fetching occupational wages");
            occWagesData = await res.json();
            renderOccWagesPane(occWagesData);
            loadedSgHubPanes["hub-occ-wages"] = true;
        } catch (err) {
            console.error("Failed to load occupational wages", err);
            container.innerHTML = `<p style='color: var(--text-error); margin:0 0 10px;'>⚠️ Failed to load occupational wage data (the MOM stats site may have briefly refused the connection).</p>
                <button id="occ-wage-retry-btn" style="background:var(--primary); color:#ffffff; font-weight:700; border:none; padding:7px 14px; border-radius:6px; font-size:12px; cursor:pointer;">
                    <i class="fa-solid fa-rotate-right"></i> Retry
                </button>`;
            document.getElementById("occ-wage-retry-btn").addEventListener("click", loadOccupationalWages);
        }
    }

    function occMoverRow(o, maxAbsPct) {
        const isPositive = o.pct_change >= 0;
        const barColor = isPositive ? "#1a7f3c" : "#c0392b";
        const barWidthPct = (Math.abs(o.pct_change) / maxAbsPct) * 100;
        return `
            <div style="display:flex; align-items:center; gap:10px; padding: 7px 0; border-bottom: 1px solid var(--border);">
                <div style="flex: 1; min-width:0;">
                    <div style="font-size:13px; font-weight:600; color: var(--text-main); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHTML(o.name)}</div>
                    <div style="font-size:11px; color: var(--text-muted);">S$${o.prior_gross.toLocaleString()} &rarr; S$${o.gross.toLocaleString()} gross/mth</div>
                </div>
                <div style="width:110px; flex-shrink:0;">
                    <div style="background: var(--bg-panel); border-radius:4px; height:8px; overflow:hidden;">
                        <div style="width:${barWidthPct}%; background:${barColor}; height:100%; border-radius:4px;"></div>
                    </div>
                </div>
                <div style="width:58px; flex-shrink:0; text-align:right; font-size:13px; font-weight:700; color:${barColor};">${isPositive ? '+' : ''}${o.pct_change.toFixed(1)}%</div>
            </div>
        `;
    }

    function renderOccWagesPane(data) {
        const container = document.getElementById("hub-occ-wages-content");
        if (!container || !data || !data.all_occupations || !data.all_occupations.length) {
            if (container) container.innerHTML = "<p style='color: var(--text-subtle); margin:0;'>Occupational wage data unavailable.</p>";
            return;
        }

        const banner = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
            <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${escapeHTML(data.synced_at || getRetrievalTimestamp())}
        </div>`;

        // ---- Derived insights (the panel leads with takeaways, not raw tables) ----
        const matched = data.all_occupations.filter(o => o.pct_change != null);
        const risingCount = matched.filter(o => o.pct_change > 0).length;
        const sortedPcts = matched.map(o => o.pct_change).sort((a, b) => a - b);
        const medianPct = sortedPcts.length ? sortedPcts[Math.floor(sortedPcts.length / 2)] : 0;
        const newTechCount = data.new_titles.filter(o => o.is_tech).length;
        const best = data.top_movers[0];
        const worst = data.bottom_movers[0];
        const topTech = data.tech_roles.find(o => o.gross);
        const topNewPaid = data.new_titles.filter(o => o.gross).slice().sort((a, b) => b.gross - a.gross)[0];

        const tiles = `
            <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px;">
                <div style="flex: 1; min-width: 160px; background: var(--bg-muted); border: 1px solid var(--border); padding: 14px; border-radius: 8px;">
                    <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 6px;">📊 OCCUPATIONS TRACKED (JUN ${escapeHTML(String(data.latest_year))})</span>
                    <strong style="font-size: 20px; color: var(--primary);">${data.occupation_count.toLocaleString()}</strong>
                </div>
                <div style="flex: 1; min-width: 160px; background: var(--bg-muted); border: 1px solid var(--border); padding: 14px; border-radius: 8px;">
                    <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 6px;">📈 TYPICAL YoY INCREMENT</span>
                    <strong style="font-size: 20px; color: ${medianPct >= 0 ? '#1a7f3c' : '#c0392b'};">${medianPct >= 0 ? '+' : ''}${medianPct.toFixed(1)}%</strong>
                    <span style="font-size: 12px; color: var(--text-muted);"> median, ${matched.length} titles</span>
                </div>
                <div style="flex: 1; min-width: 160px; background: var(--bg-muted); border: 1px solid var(--border); padding: 14px; border-radius: 8px;">
                    <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 6px;">🆕 NEW JOB TITLES VS ${escapeHTML(String(data.prior_year))}</span>
                    <strong style="font-size: 20px; color: var(--primary);">${data.new_titles.length}</strong>
                    <span style="font-size: 12px; color: var(--text-muted);"> (${newTechCount} tech/AI)</span>
                </div>
            </div>`;

        const insights = `
            <div style="background: var(--primary-soft, var(--bg-muted)); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 18px; font-size: 12.5px; color: var(--text-main); line-height: 1.6;">
                <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">💡 Key Takeaways (June ${escapeHTML(String(data.prior_year))} &rarr; June ${escapeHTML(String(data.latest_year))})</div>
                <div>• Median wages rose for <strong>${risingCount} of ${matched.length}</strong> comparable job titles (${Math.round(risingCount / Math.max(matched.length, 1) * 100)}%).</div>
                ${best ? `<div>• Sharpest rise: <strong>${escapeHTML(best.name)}</strong> at <strong style="color:#1a7f3c;">+${best.pct_change.toFixed(1)}%</strong> (S$${best.prior_gross.toLocaleString()} &rarr; S$${best.gross.toLocaleString()}); steepest decline: <strong>${escapeHTML(worst.name)}</strong> at <strong style="color:#c0392b;">${worst.pct_change.toFixed(1)}%</strong>.</div>` : ''}
                ${topNewPaid ? `<div>• The SSOC refresh added <strong>${data.new_titles.length}</strong> new job titles — ${newTechCount} of them tech/AI-era. Highest-paid newcomer: <strong>${escapeHTML(topNewPaid.name)}</strong> (S$${topNewPaid.gross.toLocaleString()}/mth).</div>` : ''}
                ${topTech ? `<div>• Top-paying tech role: <strong>${escapeHTML(topTech.name)}</strong> at <strong>S$${topTech.gross.toLocaleString()}/mth</strong> median.</div>` : ''}
            </div>`;

        // New-title chips: server sorts tech-first then by wage — show the 8 most notable
        // instead of a scrolling wall of ~45.
        const shownNewTitles = data.new_titles.slice(0, 8);
        const moreNewCount = data.new_titles.length - shownNewTitles.length;
        const newChips = shownNewTitles.map(o => `
            <span title="${escapeHTML(o.group || '')}" style="display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:600; padding: 5px 10px; border-radius: 14px; margin: 0 6px 8px 0;
                background: ${o.is_tech ? 'rgba(37, 99, 235, 0.10)' : 'var(--bg-muted)'};
                border: 1px solid ${o.is_tech ? 'var(--primary)' : 'var(--border)'}; color: var(--text-main);">
                ${o.is_tech ? '🤖 ' : ''}${escapeHTML(o.name)}${o.gross ? ` <span style="color: var(--text-muted); font-weight:700;">S$${o.gross.toLocaleString()}</span>` : ''}
            </span>`).join('');

        const techRows = data.tech_roles.filter(o => o.gross).slice(0, 5).map(o => `
            <div style="display:flex; align-items:center; gap:10px; padding: 7px 0; border-bottom: 1px solid var(--border);">
                <div style="flex: 1; min-width:0; font-size:13px; font-weight:600; color: var(--text-main); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                    ${escapeHTML(o.name)}${o.is_new ? ' <span style="font-size:10px; color: var(--primary); font-weight:700;">NEW</span>' : ''}
                </div>
                <div style="width:88px; flex-shrink:0; text-align:right; font-size:13px; font-weight:700; color: var(--text-main);">S$${o.gross.toLocaleString()}</div>
                <div style="width:58px; flex-shrink:0; text-align:right; font-size:12px; font-weight:700; color:${o.pct_change == null ? 'var(--text-muted)' : (o.pct_change >= 0 ? '#1a7f3c' : '#c0392b')};">
                    ${o.pct_change == null ? '—' : `${o.pct_change >= 0 ? '+' : ''}${o.pct_change.toFixed(1)}%`}
                </div>
            </div>`).join('');

        const upMovers = data.top_movers.slice(0, 5);
        const downMovers = data.bottom_movers.slice(0, 5);
        const maxAbsPct = Math.max(...upMovers.concat(downMovers).map(o => Math.abs(o.pct_change)), 1);

        const groups = [...new Set(data.all_occupations.map(o => o.group).filter(Boolean))].sort();
        const groupOptions = groups.map(g => `<option value="${escapeHTML(g)}">${escapeHTML(g)}</option>`).join('');

        container.innerHTML = banner + tiles + insights + `
            <div style="display:flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px;">
                <div style="flex: 1; min-width: 300px;">
                    <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">📊 Where Do Wages Sit? (${data.occupation_count} titles)</div>
                    <div id="occ-wage-hist" style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 10px 10px 4px;"></div>
                    <div id="occ-wage-hist-note" style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;"></div>
                </div>
                <div style="flex: 1; min-width: 300px;">
                    <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">🎯 Pay vs Raise — Every Occupation</div>
                    <div id="occ-wage-scatter" style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 10px 10px 4px;"></div>
                    <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                        <span><span style="display:inline-block; width:9px; height:9px; border-radius:50%; background:${CHART_SERIES[0]}; margin-right:5px;"></span>Tech / digital</span>
                        <span><span style="display:inline-block; width:9px; height:9px; border-radius:50%; background:${CHART_CONTEXT}; opacity:0.7; margin-right:5px;"></span>All other occupations</span>
                        <span>Hover any dot for the job title.</span>
                    </div>
                    <div id="occ-wage-scatter-note" style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;"></div>
                </div>
            </div>

            <div style="display:flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px;">
                <div style="flex: 1; min-width: 280px;">
                    <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">🚀 Top 5 Fastest Rising Wages (${escapeHTML(String(data.prior_year))} &rarr; ${escapeHTML(String(data.latest_year))})</div>
                    <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px;">${upMovers.map(o => occMoverRow(o, maxAbsPct)).join('')}</div>
                </div>
                <div style="flex: 1; min-width: 280px;">
                    <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">📉 Top 5 Steepest Declines (${escapeHTML(String(data.prior_year))} &rarr; ${escapeHTML(String(data.latest_year))})</div>
                    <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px;">${downMovers.map(o => occMoverRow(o, maxAbsPct)).join('')}</div>
                </div>
            </div>

            <div style="display:flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px;">
                <div style="flex: 1; min-width: 280px;">
                    <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">🤖 Top 5 Highest-Paying Tech &amp; Digital Roles</div>
                    <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px;">${techRows}</div>
                </div>
                <div style="flex: 1; min-width: 280px;">
                    <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">🆕 Notable New Job Titles (🤖 = tech/AI-era)</div>
                    <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 12px 12px 4px;">
                        ${newChips || '<p style="color: var(--text-subtle); margin:0 0 8px;">No newly created titles this edition.</p>'}
                        <div style="font-size: 10px; color: var(--text-muted); margin: 4px 0 8px;">${moreNewCount > 0 ? `+${moreNewCount} more new titles — find them in the wage lookup below. ` : ''}Renamed titles are already matched to their old rows and excluded.</div>
                    </div>
                </div>
            </div>

            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">🔎 Wage Lookup (June ${escapeHTML(String(data.latest_year))} medians)</div>
            <div style="display:flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; align-items: center;">
                <input id="occ-wage-search" type="text" placeholder="Search a job title, e.g. software, nurse, analyst..." style="flex: 2; min-width: 200px; padding: 8px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-muted); color: var(--text-main); outline: none;">
                <select id="occ-wage-group-filter" style="flex: 1; min-width: 160px; padding: 8px; font-size: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-muted); color: var(--text-main); outline: none;">
                    <option value="">All occupation groups</option>
                    ${groupOptions}
                </select>
                <select id="occ-wage-sort" style="flex: 1; min-width: 140px; padding: 8px; font-size: 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-muted); color: var(--text-main); outline: none;">
                    <option value="gross">Sort: Highest wage</option>
                    <option value="pct_desc">Sort: Best YoY increment</option>
                    <option value="pct_asc">Sort: Worst YoY increment</option>
                    <option value="name">Sort: Name A–Z</option>
                </select>
                <label style="display:inline-flex; align-items:center; gap:6px; font-size:12px; font-weight:600; color: var(--text-main); cursor:pointer; white-space:nowrap;">
                    <input id="occ-wage-tech-only" type="checkbox" style="accent-color: var(--primary);"> 🤖 Tech only
                </label>
            </div>
            <div style="display:flex; align-items:center; gap:10px; padding: 4px 16px; font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                <div style="flex: 1;">Occupation</div>
                <div style="width:88px; flex-shrink:0; text-align:right;">Gross/mth</div>
                <div style="width:58px; flex-shrink:0; text-align:right;">YoY</div>
            </div>
            <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 6px 16px; max-height: 320px; overflow-y: auto;">
                <div id="occ-wage-table-body"></div>
            </div>
            <div id="occ-wage-table-count" style="font-size: 11px; color: var(--text-muted); margin-top: 8px;"></div>
            <div style="font-size: 10px; color: var(--text-muted); margin-top: 8px;">⚠️ Survey-based figures (private-sector establishments with ≥25 employees; full-time residents) — small occupations can swing sharply year to year. 💡 Source: ${escapeHTML(data.source)}</div>
            <div style="margin-top: 14px; border-top: 1px solid var(--border); padding-top: 12px; display:flex; justify-content:flex-end;">
                <button id="occ-wage-chat-btn" data-prompt="Based on Singapore's latest MOM Occupational Wage Survey, which jobs had the best salary increment rates this year, what new AI-era job titles were created and what do they pay, and should someone in a declining occupation consider a sector change?" style="background:var(--primary); color:#ffffff; font-weight:700; border:none; padding:8px 14px; border-radius:6px; font-size:12px; cursor:pointer; transition:all 0.2s ease;">
                    <i class="fa-solid fa-robot"></i> Ask Co-Pilot for Career Insights
                </button>
            </div>
        `;

        document.getElementById("occ-wage-search").addEventListener("input", renderOccWageTableRows);
        document.getElementById("occ-wage-group-filter").addEventListener("change", renderOccWageTableRows);
        document.getElementById("occ-wage-sort").addEventListener("change", renderOccWageTableRows);
        document.getElementById("occ-wage-tech-only").addEventListener("change", renderOccWageTableRows);
        document.getElementById("occ-wage-chat-btn").addEventListener("click", askCopilotWithPrompt);
        renderOccWageTableRows();
        renderOccWageCharts(data);
    }

    function renderOccWageCharts(data) {
        const priced = data.all_occupations.filter(o => o.gross);
        const grosses = priced.map(o => o.gross).sort((a, b) => a - b);
        const medianGross = grosses[Math.floor(grosses.length / 2)] || 0;

        // Histogram: how many job titles fall in each monthly-wage band
        const bands = [
            { label: "<2k", lo: 0, hi: 2000 }, { label: "2–4k", lo: 2000, hi: 4000 },
            { label: "4–6k", lo: 4000, hi: 6000 }, { label: "6–8k", lo: 6000, hi: 8000 },
            { label: "8–10k", lo: 8000, hi: 10000 }, { label: "10–12k", lo: 10000, hi: 12000 },
            { label: "12k+", lo: 12000, hi: Infinity },
        ];
        const counts = bands.map(b => priced.filter(o => o.gross >= b.lo && o.gross < b.hi).length);
        const histEl = document.getElementById("occ-wage-hist");
        if (histEl) {
            renderBarChart(histEl, {
                labels: bands.map(b => b.label),
                values: counts,
                tooltipFor: i => `<div style="font-weight:700;">S$${bands[i].label}/mth gross</div><div><strong>${counts[i]}</strong> of ${priced.length} job titles (${Math.round(counts[i] / priced.length * 100)}%)</div>`,
            });
            const note = document.getElementById("occ-wage-hist-note");
            if (note) note.innerHTML = `💡 The median occupation earns <strong>S$${medianGross.toLocaleString()}/mth</strong> gross — half of all tracked job titles sit below that line.`;
        }

        // Scatter: wage level vs YoY change, tech roles highlighted. The median-wage line +
        // zero line split it into quadrants so the reading is explicit: top-right = jobs that
        // already pay above the median AND still got a raise.
        const scatterEl = document.getElementById("occ-wage-scatter");
        if (scatterEl) {
            const pts = priced.filter(o => o.pct_change != null).map(o => ({
                x: o.gross, y: o.pct_change, name: o.name, sub: o.group || "", highlight: o.is_tech,
            }));
            renderScatterChart(scatterEl, {
                points: pts,
                xLabel: "median gross monthly wage (S$)",
                xRef: { value: medianGross, label: `median S$${medianGross.toLocaleString()}` },
                quadrants: { tl: "↑ rising", bl: "↓ falling", tr: "high pay · rising", br: "high pay · falling" },
            });
            const inQuad = pts.filter(p => p.x >= medianGross && p.y > 0);
            const techPts = pts.filter(p => p.highlight);
            const techInQuad = inQuad.filter(p => p.highlight);
            const noteEl = document.getElementById("occ-wage-scatter-note");
            if (noteEl) noteEl.innerHTML = `💡 <strong>${inQuad.length}</strong> of ${pts.length} occupations (${Math.round(inQuad.length / pts.length * 100)}%) land in the sweet spot — above-median pay <em>and</em> a rising wage. Tech roles get there disproportionately often: <strong>${techInQuad.length} of ${techPts.length}</strong> (${Math.round(techInQuad.length / Math.max(techPts.length, 1) * 100)}%).`;
        }
    }

    // Shared "hand this prompt to the Co-Pilot" flow (same behaviour as the sector-analysis
    // button): switch to the Portals tab, pop the chat widget open, and submit the prompt.
    function askCopilotWithPrompt(event) {
        const prompt = event.currentTarget.getAttribute("data-prompt");
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
    }

    function renderOccWageTableRows() {
        const body = document.getElementById("occ-wage-table-body");
        const countEl = document.getElementById("occ-wage-table-count");
        if (!body || !occWagesData) return;

        const q = (document.getElementById("occ-wage-search")?.value || "").toLowerCase().trim();
        const grp = document.getElementById("occ-wage-group-filter")?.value || "";
        const sort = document.getElementById("occ-wage-sort")?.value || "gross";
        const techOnly = document.getElementById("occ-wage-tech-only")?.checked || false;
        const filtered = occWagesData.all_occupations.filter(o =>
            (!q || o.name.toLowerCase().includes(q)) && (!grp || o.group === grp) && (!techOnly || o.is_tech));

        // "name" keeps the server's A–Z order; wage/YoY sorts push missing values to the bottom.
        if (sort === "gross") filtered.sort((a, b) => (b.gross ?? -1) - (a.gross ?? -1));
        else if (sort === "pct_desc") filtered.sort((a, b) => (b.pct_change ?? -Infinity) - (a.pct_change ?? -Infinity));
        else if (sort === "pct_asc") filtered.sort((a, b) => (a.pct_change ?? Infinity) - (b.pct_change ?? Infinity));

        // Insight-first default: with no search/filter active this is a top-10 leaderboard for
        // the chosen sort, not a scroll through all 500+ rows; filtering expands the cap.
        const hasFilter = Boolean(q || grp || techOnly);
        const MAX_ROWS = hasFilter ? 40 : 10;
        body.innerHTML = filtered.slice(0, MAX_ROWS).map(o => `
            <div style="display:flex; align-items:center; gap:10px; padding: 6px 0; border-bottom: 1px solid var(--border);">
                <div style="flex: 1; min-width:0;">
                    <div style="font-size:13px; font-weight:600; color: var(--text-main); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                        ${escapeHTML(o.name)}${o.is_new ? ' <span style="font-size:10px; color: var(--primary); font-weight:700;">NEW</span>' : ''}${o.is_tech ? ' 🤖' : ''}
                    </div>
                    <div style="font-size:10px; color: var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHTML(o.group || '')}</div>
                </div>
                <div style="width:88px; flex-shrink:0; text-align:right; font-size:13px; font-weight:700; color: var(--text-main);">${o.gross ? `S$${o.gross.toLocaleString()}` : '—'}</div>
                <div style="width:58px; flex-shrink:0; text-align:right; font-size:12px; font-weight:700; color:${o.pct_change == null ? 'var(--text-muted)' : (o.pct_change >= 0 ? '#1a7f3c' : '#c0392b')};">
                    ${o.pct_change == null ? '—' : `${o.pct_change >= 0 ? '+' : ''}${o.pct_change.toFixed(1)}%`}
                </div>
            </div>`).join('') || '<p style="color: var(--text-subtle); margin: 8px 0;">No occupations match your search.</p>';

        const sortLabels = { gross: "highest-paid", pct_desc: "best-increment", pct_asc: "worst-increment", name: "A–Z" };
        countEl.textContent = !hasFilter
            ? `Top ${Math.min(MAX_ROWS, filtered.length)} ${sortLabels[sort] || ""} of ${filtered.length} occupations — search or filter to explore the rest.`
            : (filtered.length > MAX_ROWS
                ? `Showing ${MAX_ROWS} of ${filtered.length} matching occupations — refine your search to narrow down.`
                : `${filtered.length} matching occupation${filtered.length === 1 ? '' : 's'}.`);
    }

    function renderRetrenchmentPane(retrenchment) {
        const headlineEl = document.getElementById("retrenchment-headline");
        const detailsEl = document.getElementById("retrenchment-details");
        const sourceEl = document.getElementById("retrenchment-source");
        if (!retrenchment || !headlineEl) return;

        const syncedEl = document.getElementById("retrenchment-synced");
        if (syncedEl) {
            syncedEl.innerHTML = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
                <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${escapeHTML(retrenchment.synced_at || getRetrievalTimestamp())}
            </div>`;
        }

        // headline looks like "3,590 workers (2025-Q4)" — split the count from the quarter label
        const match = retrenchment.headline.match(/^(.*?)\s*\(([^)]+)\)\s*$/);
        const workerCount = match ? match[1] : retrenchment.headline;
        const quarterRaw = match ? match[2] : "";
        const quarterLabel = quarterRaw.includes("-")
            ? `${quarterRaw.split("-")[1]} ${quarterRaw.split("-")[0]}`
            : quarterRaw;

        headlineEl.textContent = workerCount;
        detailsEl.textContent = `Primarily in ${retrenchment.industries}.`;
        sourceEl.innerHTML = `<i class="fa-regular fa-calendar"></i> Data as of: ${escapeHTML(quarterLabel)}`;
    }

    function renderHdbLaunches(text) {
        if (!text) return "<p style='color: var(--text-subtle); margin:0;'>No launches listed.</p>";

        // Header line looks like "--- [HDB BTO LAUNCH REGISTRY — June 2026 BTO Sales Exercise] ---"
        const headerMatch = text.match(/HDB BTO LAUNCH REGISTRY[^\]]*—\s*([^\]]+)\]/);
        const exerciseLabel = headerMatch ? headerMatch[1].trim() : "";
        const summaryMatch = text.match(/📊\s*([^\n]+)/);
        const summaryLine = summaryMatch ? summaryMatch[1].trim() : "";

        let html = "";
        if (summaryLine) {
            html += `<p style="font-size:13px; color: var(--text-muted); margin: 0 0 14px 0;">${escapeHTML(summaryLine)}</p>`;
        }

        const blocks = text.split("🏢");
        blocks.forEach(block => {
            if (!block.trim()) return;
            const lines = block.split("\n");
            const titleLine = lines[0].trim();
            if (titleLine.includes("HDB BTO LAUNCH REGISTRY") || titleLine.includes("CPF HOUSING GRANTS")) return; // skip header and grant block in text

            let town = "N/A";
            let classification = "Standard";
            let flatTypes = "N/A";
            lines.forEach(line => {
                const clean = line.replace(/^\s*•\s*/, '').trim();
                if (clean.includes("Town:")) town = clean.split("Town:")[1].trim();
                else if (clean.includes("Classification:")) classification = clean.split("Classification:")[1].trim();
                else if (clean.includes("FlatTypes:")) flatTypes = clean.split("FlatTypes:")[1].trim();
            });

            const cleanTitle = titleLine.split('(')[0].trim();

            const badgeStyles = {
                "Prime": "background: #fdf2f2; color: #9b1c1c; border: 1px solid #f8b4b4;",
                "Plus": "background: #e1effe; color: #1e429f; border: 1px solid #a4cafe;",
                "Standard": "background: #f3f4f6; color: #374151; border: 1px solid #d1d5db;"
            };
            const categoryBadge = `<span style="${badgeStyles[classification] || badgeStyles.Standard} padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase;">${escapeHTML(classification)}</span>`;
            const exerciseBadge = exerciseLabel ? `<span style="display:inline-flex; align-items:center; gap:4px; font-size:11px; background: var(--bg-muted); border:1px solid var(--border); color:var(--text-muted); padding: 3px 8px; border-radius:12px; font-weight:600;"><i class='fa-regular fa-calendar'></i> ${escapeHTML(exerciseLabel)}</span>` : '';

            html += `
            <div style="background: #ffffff; border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin-bottom: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02); display: flex; flex-direction: column; gap: 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; border-bottom: 1px solid var(--border); padding-bottom:10px;">
                    <strong style="color: var(--text-main); font-size:16px; font-weight:700; display:flex; align-items:center; gap:6px; margin:0;">
                        🏢 ${escapeHTML(cleanTitle)}
                    </strong>
                    <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">${exerciseBadge}${categoryBadge}</div>
                </div>
                <div style="font-size:13px; line-height: 1.6; color: var(--text-main); display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:12px;">
                    <div>
                        <span style="color:var(--text-muted); font-weight:600; display:block; font-size:11px; text-transform:uppercase;">📍 Town</span>
                        <span style="font-size:13px; font-weight:600; color:var(--text-main);">${escapeHTML(town)}</span>
                    </div>
                    <div style="grid-column: span 2;">
                        <span style="color:var(--text-muted); font-weight:600; display:block; font-size:11px; text-transform:uppercase;">💵 Flat Types &amp; Starting Prices (with grants)</span>
                        <span style="font-size:13px; font-weight:700; color:var(--text-success);">${escapeHTML(flatTypes)}</span>
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
        const vacPct = Math.min((vacNum / 30000) * 100, 100);

        // Everything shown here is real MOM job vacancy data (BigQuery / data.gov.sg). The
        // former illustrative fields (median salary, skills, risk level, drivers, schemes)
        // were removed — hardcoded figures don't belong next to live ones.
        const trendPctNum = parseFloat(details.trend_pct) || 0;
        const growthRate = details.trend_pct !== "N/A"
            ? `${trendPctNum >= 0 ? "▲" : "▼"} ${details.trend_pct} YoY`
            : "N/A";
        const growthColor = trendPctNum >= 0 ? "#10b981" : "#f59e0b"; // green if growing, amber if declining — matches the real trend sign

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

            <div style="background: var(--bg-muted); border: 1px solid var(--border); padding: 10px; border-radius: 6px; margin-bottom: 12px; max-width: 260px;">
                <span style="font-size: 10px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 4px; text-transform: uppercase;">📈 YoY Growth Index</span>
                <strong style="font-size: 14px; color: ${growthColor};">${growthRate}</strong>
            </div>

            <div style="border-top: 1px solid var(--border); padding-top: 12px; margin-top: 12px; font-size:12px; color: var(--text-muted); line-height:1.5;">
                <strong>📈 Industry Outlook:</strong> ${escapeHTML(details.trend)}
            </div>
            <div style="font-size:10px; color: var(--text-muted); margin-top:10px;">ℹ️ All figures are live MOM Job Vacancy data (BigQuery / data.gov.sg); the forecast is a naive YoY extrapolation. For wages per job title, see the Occupational Wage Explorer below.</div>

            <div style="margin-top: 16px; border-top: 1px solid var(--border); padding-top: 12px; display:flex; justify-content:flex-end;">
                <button class="chat-sector-btn" data-prompt="Analyze the latest job market trends, active vacancies and typical wages in Singapore's ${sector} sector" style="background:var(--primary); color:#ffffff; font-weight:700; border:none; padding:8px 14px; border-radius:6px; font-size:12px; cursor:pointer; transition:all 0.2s ease;">
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
                loadSgHubPaneData("hub-transport-pane");
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
