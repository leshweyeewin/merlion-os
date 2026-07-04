// Sanitize any string before inserting into innerHTML to prevent XSS
function escapeHTML(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
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
            const trimmed = url.trim().toLowerCase();
            if (trimmed.startsWith('javascript:') || trimmed.startsWith('data:')) {
                return escapeHTML(label);
            }
            return `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`;
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

    async function loadSgHubData() {
        try {
            const res = await fetch("/api/sg-hub");
            if (!res.ok) throw new Error("API response error");
            const data = await res.json();
            
            // 1. Render Weather / PSI
            let envHtml = "";
            const envLines = data.environment.split("\n\n");
            envLines.forEach(block => {
                const lines = block.split("\n");
                const title = lines[0].replace(/---/g, '').trim();
                let body = lines.slice(1).join("<br>");
                
                if (title.includes("PSI")) {
                    body = body.replace("🍃", "<span style='font-size:16px;'>🍃</span>");
                    envHtml += `<div style="margin-bottom: 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px;">
                        <strong style="color: var(--text-success); display:block; margin-bottom: 4px; font-size:14px;">${escapeHTML(title)}</strong>
                        <span style="line-height:1.6; color: var(--text-muted);">${body}</span>
                    </div>`;
                } else {
                    body = body.replace("⛅", "<span style='font-size:16px;'>⛅</span>");
                    envHtml += `<div>
                        <strong style="color: var(--link); display:block; margin-bottom: 4px; font-size:14px;">${escapeHTML(title)}</strong>
                        <span style="line-height:1.6; color: var(--text-muted);">${body}</span>
                    </div>`;
                }
            });
            weatherContent.innerHTML = envHtml || "<p style='color: var(--text-subtle); margin:0;'>No active advisories.</p>";

            // 2. Render Official Gov Broadcasts
            let govHtml = "";
            data.gov_events.forEach(evt => {
                govHtml += `<div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-size: 13px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 6px; font-weight:600;">
                        <span style="color: var(--primary);"><i class="fa-solid fa-bullhorn"></i> ${escapeHTML(evt.source)}</span>
                        <a href="${evt.link}" target="_blank" style="color: var(--link); text-decoration:none;"><i class="fa-solid fa-up-right-from-square"></i> View Alert</a>
                    </div>
                    <div style="color: var(--text-main); line-height:1.45;">${escapeHTML(evt.content)}</div>
                </div>`;
            });
            govEventsContent.innerHTML = govHtml || "<p style='color: var(--text-subtle); margin:0;'>No official alerts within the last 24 hours.</p>";

            // 3. Render Community Deals & Events (Kiasu SG)
            let commHtml = "";
            data.community_events.forEach(evt => {
                commHtml += `<div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-size: 13px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 6px; font-weight:600;">
                        <span style="color: var(--link);"><i class="fa-solid fa-tags"></i> ${escapeHTML(evt.source)}</span>
                        <a href="${evt.link}" target="_blank" style="color: var(--link); text-decoration:none;"><i class="fa-solid fa-up-right-from-square"></i> View Post</a>
                    </div>
                    <div style="color: var(--text-main); line-height:1.45;">${escapeHTML(evt.content)}</div>
                </div>`;
            });
            communityEventsContent.innerHTML = commHtml || "<p style='color: var(--text-subtle); margin:0;'>No community updates within the last 24 hours.</p>";

            // 4. Filter & Render MRT / Transport alerts from gov and community events
            let mrtHtml = "";
            const transitKeywords = ["mrt", "lrt", "train", "track fault", "service delay", "smrt", "sbs transit", "lta", "road closure", "traffic accident", "delay", "disruption", "service recovery"];
            const allEvents = [...data.gov_events, ...data.community_events];
            let transitEvents = [];
            
            allEvents.forEach(evt => {
                const textLower = evt.content.toLowerCase();
                const matched = transitKeywords.some(kw => textLower.includes(kw));
                if (matched && !transitEvents.some(te => te.content === evt.content)) {
                    transitEvents.push(evt);
                }
            });

            transitEvents.forEach(evt => {
                mrtHtml += `<div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-size: 13px; margin-bottom: 8px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 6px; font-weight:600;">
                        <span style="color: var(--primary);"><i class="fa-solid fa-train-subway"></i> ${escapeHTML(evt.source)}</span>
                        <a href="${evt.link}" target="_blank" style="color: var(--link); text-decoration:none;"><i class="fa-solid fa-up-right-from-square"></i> View Alert</a>
                    </div>
                    <div style="color: var(--text-main); line-height:1.45;">${escapeHTML(evt.content)}</div>
                </div>`;
            });
            mrtEventsContent.innerHTML = mrtHtml || `
                <div style="display:flex; align-items:center; gap:8px; color: var(--text-success); background: var(--bg-muted); border: 1px solid var(--border); padding:16px; border-radius:8px; font-size:14px; font-weight:600;">
                    <i class="fa-solid fa-circle-check" style="font-size:18px;"></i>
                    🟢 All train services are operating normally. No active disruptions reported in the last 24 hours.
                </div>`;

            // 5. Render HDB BTO Launches list
            hdbLaunchesContent.innerHTML = renderHdbLaunches(data.hdb);

            // 6. Keep jobs data for dynamic switching
            sgHubJobsData = data.jobs;
            renderSectorDetails("tech"); // Default to Tech
            
            sgHubLoaded = true;
        } catch (err) {
            console.error("Failed to load SG Hub:", err);
            weatherContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load environment metrics.</p>";
            govEventsContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to retrieve official gov feeds.</p>";
            communityEventsContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to retrieve community feeds.</p>";
            mrtEventsContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load transit feeds.</p>";
            hdbLaunchesContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load upcoming launches.</p>";
            jobsContent.innerHTML = "<p style='color: var(--text-error); margin:0;'>⚠️ Failed to load employment statistics.</p>";
        }
    }

    function renderHdbLaunches(text) {
        if (!text) return "<p style='color: var(--text-subtle); margin:0;'>No launches listed.</p>";
        let html = "";
        const blocks = text.split("🏢");
        blocks.forEach(block => {
            if (!block.trim()) return;
            const lines = block.split("\n");
            const titleLine = lines[0].trim();
            if (titleLine.includes("CPF HOUSING GRANTS")) return; // skip grant block in text
            
            let loc = "N/A";
            let units = "N/A";
            let pricing = "N/A";
            lines.forEach(line => {
                const clean = line.replace(/^\s*•\s*/, '').trim();
                if (clean.includes("Location:")) loc = clean.split("Location:")[1].trim();
                else if (clean.includes("Units:")) units = clean.split("Units:")[1].trim();
                else if (clean.includes("Pricing:")) pricing = clean.split("Pricing:")[1].trim();
            });
            html += `<div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                <strong style="color: var(--primary); font-size:15px; display:block; margin-bottom: 6px;">🏢 ${escapeHTML(titleLine)}</strong>
                <div style="font-size:13px; line-height: 1.5; color: var(--text-main);">
                    <strong>📍 Location:</strong> ${escapeHTML(loc)}<br>
                    <strong>📊 Supply:</strong> ${escapeHTML(units)}<br>
                    <strong>💵 Price Guide:</strong> <span style="color:var(--text-success); font-weight:700;">${escapeHTML(pricing)}</span>
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

        jobsContent.innerHTML = `
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
                <strong>📈 Industry Outlook &amp; Partition:</strong><br>
                <code style="background: var(--bg-panel); border: 1px solid var(--border); padding:2px 6px; border-radius:4px; font-size:10px; color: var(--text-success); font-family: monospace; display:inline-block; margin: 4px 0;">sg_employment.vacancies_${sector}</code><br>
                ${escapeHTML(details.trend)}
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
            if (!sgHubLoaded) {
                loadSgHubData();
            }
        });
    }

    // Job Sector switcher click handling
    sectorTabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            sectorTabButtons.forEach(b => {
                b.classList.remove("active-sector");
            });
            btn.classList.add("active-sector");
            
            const sector = btn.getAttribute("data-sector");
            renderSectorDetails(sector);
        });
    });
}

// Initialize SG Hub features on load
document.addEventListener("DOMContentLoaded", () => {
    initSgHub();
});
