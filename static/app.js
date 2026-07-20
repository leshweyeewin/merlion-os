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

// --- Singapore Progressive Tax Brackets (YA2026) ---
const TAX_BRACKETS = [
    { limit: 20000, rate: 0.00 },  // First S$20,000 (tax-free)
    { limit: 10000, rate: 0.02 },  // 20,001 to 30,000
    { limit: 10000, rate: 0.035 }, // 30,001 to 40,000
    { limit: 40000, rate: 0.07 },  // 40,001 to 80,000
    { limit: 40000, rate: 0.115 }, // 80,001 to 120,000
    { limit: 40000, rate: 0.15 },  // 120,001 to 160,000
    { limit: 40000, rate: 0.18 },  // 160,001 to 200,000
    { limit: 40000, rate: 0.19 },  // 200,001 to 240,000
    { limit: 40000, rate: 0.195 }, // 240,001 to 280,000
    { limit: 40000, rate: 0.20 },  // 280,001 to 320,000
    { limit: 180000, rate: 0.22 }, // 320,001 to 500,000
    { limit: 500000, rate: 0.23 }, // 500,001 to 1,000,000
    { limit: Infinity, rate: 0.24 } // Above 1,000,000
];

// --- Tax Calculation Helper ---
function calculateSingaporeTax(chargeableIncome) {
    if (chargeableIncome <= 20000) return 0;
    const brackets = TAX_BRACKETS;
    let tax = 0;
    let tempIncome = chargeableIncome - 20000;

    for (let i = 1; i < brackets.length; i++) {
        const b = brackets[i];
        if (tempIncome <= 0) break;
        const taxableAmount = Math.min(tempIncome, b.limit);
        tax += taxableAmount * b.rate;
        tempIncome -= taxableAmount;
    }
    return tax;
}

document.addEventListener("DOMContentLoaded", () => {
    initPortalReordering();
    initPortalVisibility();
    initPortalSearch();

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
            conversationHistory.push({ role: "user", content: text });
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
function initPortalSearch() {
    const input = document.getElementById("portal-search-input");
    const clearBtn = document.getElementById("portal-search-clear");
    const statusEl = document.getElementById("portal-search-status");
    const chipsEl = document.getElementById("quick-task-chips");
    const hubSuggestEl = document.getElementById("portal-search-hub-suggestion");
    const grid = document.querySelector(".grid-container");
    if (!input || !grid) return;

    // Everyday-language synonyms per agency, so nobody needs to know the official
    // government term to find the right portal ("change shop address" → ACRA, not
    // "Change in Registered Office Address"). Agencies not listed still match on
    // their card name/description.
    const PORTAL_INTENTS = {
        ica: "renew passport apply passport nric identity card citizenship pr permanent resident immigration checkpoint travel entry visa long term pass",
        eld: "vote voting election voter register ballot",
        iras: "income tax file taxes pay tax property tax stamp duty refund tax relief notice of assessment noa tax bill season",
        cpf: "retirement savings top up medisave ordinary account special account housing withdrawal repayment loan repay nomination contribution",
        redeemsg: "cdc voucher climate voucher redeem vouchers claim free",
        spgroup: "electricity water gas utilities bill open account meter power",
        skillsfuture: "course subsidy credits learn upskill training claim skillsfuture find courses",
        wsg: "job search find job career change switch unemployed career coach mid career conversion",
        mom: "work pass employment pass work permit s pass foreign worker levy maid helper employment law salary dispute overtime retrenchment fired dismissal notice",
        moh: "hospital polyclinic subsidy healthcare medical fees ward",
        hdb: "buy flat apply bto flat resale hdb grant housing loan hle season parking rent room sell flat upgrading",
        moe: "primary school registration secondary school scholarship school fees financial assistance",
        lta: "road tax coe vehicle car driving licence registration erp season parking onemotoring motorcycle vep",
        nea: "dengue haze psi air quality mosquito hawker licence funeral cremation weather forecast",
        govsg: "budget announcement national policy news",
        sgjourney: "new citizen citizenship journey onboarding",
        onemap: "map address school distance boundary grc smc find nearest",
        healthhub: "health records appointment medication refill clinic booking screening results healthier sg",
        activesg: "gym pool swimming badminton court sports facility booking free credits",
        hpb: "healthy 365 challenge steps rewards health screening vaccination",
        msf: "comcare financial help assistance baby bonus childcare leave family violence support",
        pub: "water bill flood drain used water conservation rebate",
        nlb: "library borrow books ebooks study room",
        ura: "zoning master plan land use development shophouse conservation car park grant",
        nparks: "bbq pit campsite camping permit park booking garden tree",
        mas: "savings bonds ssb tbill treasury invest bank complaint moneysense financial institution",
        imda: "sms scam spam call telco complaint sender id blocking",
        ns: "ns national service ord ict enlistment reservist deferment mr exit permit",
        spf: "police report traffic fine certificate of clearance coc stolen lost scam report crime",
        scdf: "fire safety certificate ambulance shelter cpr aed myresponder",
        acra: "register company business registration bizfile annual return change company address registered office close company strike off director",
        enterprisesg: "sme grant business grant psg edg trade export startup",
        ipos: "trademark patent brand copyright design protect idea",
        sla: "land title deed property ownership inlis state land lease",
        cea: "property agent check agent licence complaint commission",
        pa: "community club cc courses interest group facility booking passion card",
        mindef: "army saf defence military",
        seab: "psle o level a level exam results private candidate",
        judiciary: "court case hearing small claims tribunal",
        mlaw: "divorce probate will deed poll legal aid bankruptcy moneylender",
        sgenable: "disability support grants assistive technology special needs",
        mfa: "overseas travel advisory embassy consulate register trip eregister",
        sfa: "food safety recall import licence home based food",
        gra: "casino entry levy exclusion gambling",
        nac: "busking licence arts grant",
        mccy: "charity donation volunteer youth",
    };

    // Live-data panels & calculators inside SG Hub that answer the same intents —
    // surfaced as a clickable suggestion so users learn the data is one tab away.
    const HUB_SUGGESTIONS = [
        { terms: "coe car vehicle premium bidding taxi price", label: "🚗 Live COE premiums & taxi availability", pane: "hub-transport-pane" },
        { terms: "mrt train delay disruption breakdown transit alert checkpoint woodlands tuas flood", label: "🚇 Live MRT status, checkpoint & flood alerts", pane: "hub-gov-transit-pane" },
        { terms: "bto flat resale price housing grant ehg launch accrued interest", label: "🏠 BTO launches, resale price trends & grant calculators", pane: "hub-hdb-pane" },
        { terms: "job vacancy salary wage pay retrenchment career hiring increment", label: "📊 Live job market, wages & retrenchment data", pane: "hub-jobs-pane" },
        { terms: "tax deadline relief srs cpf top up optimizer bracket filing due", label: "⚖️ Tax deadlines & relief optimizer", pane: "hub-tax-pane" },
        { terms: "deal promo discount lobang food event", label: "🎟️ Community deals & meetups", pane: "hub-community-pane" },
        { terms: "weather rain forecast psi haze air uv temperature humidity", label: "🌤️ Live weather, PSI & UV index", pane: "hub-env-pane" },
    ];

    const QUICK_TASKS = [
        "Renew passport", "File income tax", "Top up CPF", "CDC vouchers",
        "Apply for BTO", "Road tax & COE", "Register a company", "Find courses", "Check NS status",
    ];

    const searchIndex = Array.from(grid.querySelectorAll(".service-card")).map(card => ({
        card,
        text: [
            card.querySelector("h3")?.textContent || "",
            card.querySelector("p")?.textContent || "",
            card.querySelector(".card-desc")?.textContent || "",
            PORTAL_INTENTS[card.dataset.agency] || "",
        ].join(" ").toLowerCase(),
    }));

    // Filler words carry no routing signal and, via substring matching, light up half the
    // grid ("to" is inside "electoral") — strip them before scoring.
    const SEARCH_STOPWORDS = new Set([
        "how", "to", "do", "i", "my", "the", "a", "an", "of", "in", "on", "for", "and",
        "or", "is", "it", "me", "can", "what", "where", "when", "back", "get", "with",
    ]);
    const tokenize = q => {
        const all = q.toLowerCase().split(/[^a-z0-9]+/).filter(t => t.length >= 2);
        const kept = all.filter(t => !SEARCH_STOPWORDS.has(t));
        return kept.length ? kept : all; // an all-stopword query still searches literally
    };

    function applySearch(query) {
        const toks = tokenize(query);
        clearBtn.classList.toggle("hidden", !query);
        if (!toks.length) {
            searchIndex.forEach(e => e.card.classList.remove("search-dim"));
            statusEl.classList.add("hidden");
            hubSuggestEl.classList.add("hidden");
            return;
        }

        // Strict pass first (every word must match); if nothing survives, relax — but still
        // demand at least two matching words when the query has several, so one incidental
        // substring hit doesn't surface a card.
        let matches = searchIndex.filter(e => toks.every(t => e.text.includes(t)));
        if (!matches.length) {
            const need = Math.min(2, toks.length);
            matches = searchIndex.filter(e => toks.filter(t => e.text.includes(t)).length >= need);
        }
        const matchSet = new Set(matches.map(m => m.card));

        let shown = 0, hiddenHits = 0;
        searchIndex.forEach(e => {
            const hit = matchSet.has(e.card);
            e.card.classList.toggle("search-dim", !hit);
            if (hit && e.card.classList.contains("portal-hidden")) hiddenHits++;
            else if (hit) shown++;
        });

        statusEl.classList.remove("hidden");
        statusEl.textContent = shown
            ? `Showing ${shown} matching portal${shown === 1 ? "" : "s"}`
            + (hiddenHits ? ` (+${hiddenHits} in your hidden list — see Manage Portals)` : "")
            : (hiddenHits
                ? `All ${hiddenHits} matching portal${hiddenHits === 1 ? " is" : "s are"} in your hidden list — see Manage Portals`
                : "No portals match — try different words, or ask the Co-Pilot below");

        // Best-scoring SG Hub panel suggestion — use whole-word matching so
        // "tax" doesn't fire on "taxi", "check" doesn't fire on "checkpoint", etc.
        let best = null, bestScore = 0;
        HUB_SUGGESTIONS.forEach(s => {
            const termWords = s._termWords || (s._termWords = new Set(s.terms.split(/\s+/)));
            const score = toks.filter(t => termWords.has(t)).length;
            if (score > bestScore) { bestScore = score; best = s; }
        });
        if (best) {
            hubSuggestEl.classList.remove("hidden");
            hubSuggestEl.innerHTML = `${escapeHTML(best.label)} <span style="margin-left:auto; color: var(--primary); white-space:nowrap;">Open in SG Hub <i class="fa-solid fa-arrow-right"></i></span>`;
            hubSuggestEl.onclick = () => {
                document.getElementById("main-tab-hub-btn")?.click();
                document.querySelector(`.hub-sub-tab-btn[data-hub-sub-tab="${best.pane}"]`)?.click();
                window.scrollTo({ top: 0, behavior: "smooth" });
            };
        } else {
            hubSuggestEl.classList.add("hidden");
        }
    }

    QUICK_TASKS.forEach(task => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "quick-task-chip";
        chip.textContent = task;
        chip.addEventListener("click", () => {
            const active = chip.classList.contains("active-chip");
            chipsEl.querySelectorAll(".quick-task-chip").forEach(c => c.classList.remove("active-chip"));
            input.value = active ? "" : task;
            if (!active) chip.classList.add("active-chip");
            applySearch(input.value);
        });
        chipsEl.appendChild(chip);
    });

    let searchTimer = null;
    input.addEventListener("input", () => {
        chipsEl.querySelectorAll(".quick-task-chip").forEach(c => c.classList.remove("active-chip"));
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => applySearch(input.value), 150);
    });
    input.addEventListener("keydown", e => { if (e.key === "Escape") { input.value = ""; applySearch(""); } });
    clearBtn.addEventListener("click", () => {
        input.value = "";
        chipsEl.querySelectorAll(".quick-task-chip").forEach(c => c.classList.remove("active-chip"));
        applySearch("");
        input.focus();
    });
}

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

    function cardDesc(card) {
        const d = card.querySelector(".card-desc");
        return d ? d.textContent.trim() : "";
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

    // --- Manage Portals panel: search + multi-select + bulk add-back / hide ---
    let panelMode = "hidden";   // "hidden" = restore portals, "visible" = hide portals
    let panelQuery = "";
    const selected = new Set();

    function allCards() {
        return Array.from(grid.querySelectorAll(".service-card"));
    }

    function matchesQuery(card) {
        if (!panelQuery) return true;
        const q = panelQuery.toLowerCase();
        return cardName(card).toLowerCase().includes(q) || cardDesc(card).toLowerCase().includes(q);
    }

    function renderDropdown() {
        const hiddenSet = new Set(loadHidden());
        const inScope = allCards().filter(card =>
            (panelMode === "hidden") === hiddenSet.has(card.dataset.agency) && matchesQuery(card)
        );
        const totalScope = allCards().length;
        const visibleCount = totalScope - hiddenSet.size;
        const hiddenCount = hiddenSet.size;

        if (inScope.length === 0) {
            dropdown.innerHTML = `
                <div class="mp-search"><input type="text" id="mp-search-input" placeholder="Search name or description…" autocomplete="off" value="${escapeHTML(panelQuery)}"></div>
                <div class="mp-modes">
                    <button type="button" class="mp-mode-btn ${panelMode === 'hidden' ? 'active' : ''}" data-mode="hidden">Hidden (${hiddenCount})</button>
                    <button type="button" class="mp-mode-btn ${panelMode === 'visible' ? 'active' : ''}" data-mode="visible">Visible (${visibleCount})</button>
                </div>
                <div class="hidden-portals-empty" style="margin: 12px 0;">No matching portals.</div>
                <div class="mp-actions" style="margin-top: 6px; border-top: 1px dashed var(--border); padding-top: 6px;">
                    <button type="button" class="mp-bulk-btn mp-add" id="mp-show-all-global" style="background:#16a34a;">Show All Portals</button>
                    <button type="button" class="mp-bulk-btn mp-hide" id="mp-hide-all-global">Hide All Portals</button>
                </div>`;
            return;
        }

        const allSelected = inScope.every(c => selected.has(c.dataset.agency));
        const rows = inScope.map(card => {
            const agency = card.dataset.agency;
            const checked = selected.has(agency) ? "checked" : "";
            return `<label class="mp-row">
                <input type="checkbox" class="mp-check" data-agency="${escapeHTML(agency)}" ${checked}>
                <span class="mp-row-name">${escapeHTML(cardName(card))}</span>
                <span class="mp-row-desc">${escapeHTML(cardDesc(card))}</span>
            </label>`;
        }).join('');

        dropdown.innerHTML = `
            <div class="mp-search"><input type="text" id="mp-search-input" placeholder="Search name or description…" autocomplete="off" value="${escapeHTML(panelQuery)}"></div>
            <div class="mp-modes">
                <button type="button" class="mp-mode-btn ${panelMode === 'hidden' ? 'active' : ''}" data-mode="hidden">Hidden (${hiddenCount})</button>
                <button type="button" class="mp-mode-btn ${panelMode === 'visible' ? 'active' : ''}" data-mode="visible">Visible (${visibleCount})</button>
            </div>
            <label class="mp-row mp-selectall">
                <input type="checkbox" id="mp-selectall" ${allSelected ? 'checked' : ''}>
                <span class="mp-row-name"><strong>Select all (${inScope.length})</strong></span>
            </label>
            <div class="mp-list">${rows}</div>
            <div class="mp-actions">
                <button type="button" class="mp-bulk-btn mp-add" id="mp-bulk-add">${panelMode === 'hidden' ? 'Add back selected' : 'Show selected'}</button>
                <button type="button" class="mp-bulk-btn mp-hide" id="mp-bulk-hide">${panelMode === 'hidden' ? 'Hide all listed' : 'Hide selected'}</button>
            </div>
            <div class="mp-actions" style="margin-top: 6px; border-top: 1px dashed var(--border); padding-top: 6px;">
                <button type="button" class="mp-bulk-btn mp-add" id="mp-show-all-global" style="background:#16a34a;">Show All Portals</button>
                <button type="button" class="mp-bulk-btn mp-hide" id="mp-hide-all-global">Hide All Portals</button>
            </div>`;
    }

    function bulkApply(agencies, action) {
        agencies.forEach(a => action(a));
        selected.clear();
        updateBadge();
        renderDropdown();
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
    }

    function showPortal(agency) {
        saveHidden(loadHidden().filter(a => a !== agency));
        const card = grid.querySelector(`.service-card[data-agency="${agency}"]`);
        if (card) card.classList.remove("portal-hidden");
        updateBadge();
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
            if (dropdown && !dropdown.classList.contains("hidden")) renderDropdown();
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
            if (willOpen) { selected.clear(); renderDropdown(); }
            dropdown.classList.toggle("hidden", !willOpen);
        });

        // Delegated handlers for the panel
        dropdown.addEventListener("input", (e) => {
            if (e.target.id === "mp-search-input") {
                panelQuery = e.target.value;
                const start = e.target.selectionStart;
                const end = e.target.selectionEnd;
                selected.clear();
                renderDropdown();
                const inp = dropdown.querySelector("#mp-search-input");
                if (inp) {
                    inp.focus();
                    try { inp.setSelectionRange(start, end); } catch (err) { }
                }
            }
        });
        dropdown.addEventListener("click", (e) => {
            const modeBtn = e.target.closest(".mp-mode-btn");
            if (modeBtn) {
                panelMode = modeBtn.dataset.mode;
                selected.clear();
                renderDropdown();
                return;
            }
            const showAllGlobBtn = e.target.closest("#mp-show-all-global");
            if (showAllGlobBtn) {
                const list = allCards().map(c => c.dataset.agency);
                bulkApply(list, showPortal);
                return;
            }
            const hideAllGlobBtn = e.target.closest("#mp-hide-all-global");
            if (hideAllGlobBtn) {
                const list = allCards().map(c => c.dataset.agency);
                bulkApply(list, hidePortal);
                return;
            }
            const addBtn = e.target.closest("#mp-bulk-add");
            if (addBtn) {
                const hiddenSet = new Set(loadHidden());
                const targets = allCards().filter(c =>
                    ((panelMode === "hidden") === hiddenSet.has(c.dataset.agency)) &&
                    matchesQuery(c) && selected.has(c.dataset.agency)
                ).map(c => c.dataset.agency);
                const list = targets.length ? targets : allCards()
                    .filter(c => ((panelMode === "hidden") === hiddenSet.has(c.dataset.agency)) && matchesQuery(c))
                    .map(c => c.dataset.agency);
                bulkApply(list, showPortal);
                return;
            }
            const hideBtn = e.target.closest("#mp-bulk-hide");
            if (hideBtn) {
                const hiddenSet = new Set(loadHidden());
                const targets = allCards().filter(c =>
                    ((panelMode === "hidden") === hiddenSet.has(c.dataset.agency)) &&
                    matchesQuery(c) && selected.has(c.dataset.agency)
                ).map(c => c.dataset.agency);
                // In "hidden" mode the visible rows are the listed ones; bulk hide hides them.
                const list = targets.length ? targets : allCards()
                    .filter(c => ((panelMode === "hidden") === hiddenSet.has(c.dataset.agency)) && matchesQuery(c))
                    .map(c => c.dataset.agency);
                bulkApply(list, hidePortal);
                return;
            }
        });
        dropdown.addEventListener("change", (e) => {
            if (e.target.classList.contains("mp-check")) {
                const a = e.target.dataset.agency;
                if (e.target.checked) selected.add(a); else selected.delete(a);
            } else if (e.target.id === "mp-selectall") {
                const hiddenSet = new Set(loadHidden());
                const inScope = allCards().filter(c =>
                    ((panelMode === "hidden") === hiddenSet.has(c.dataset.agency)) && matchesQuery(c)
                );
                if (e.target.checked) inScope.forEach(c => selected.add(c.dataset.agency));
                else inScope.forEach(c => selected.delete(c.dataset.agency));
                renderDropdown();
            }
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
    const taxDeadlinesContent = document.getElementById("hub-tax-deadlines");
    const calcTaxOptBtn = document.getElementById("calc-tax-opt-btn");
    const taxAssessableIncome = document.getElementById("tax-assessable-income");
    const taxTopupBudget = document.getElementById("tax-topup-budget");
    const taxResidencyStatus = document.getElementById("tax-residency-status");
    const taxOptimizerResults = document.getElementById("tax-optimizer-results");
    const taxCpfCap = document.getElementById("tax-cpf-cap");
    const taxSrsCap = document.getElementById("tax-srs-cap");
    const taxSrsCapHint = document.getElementById("tax-srs-cap-hint");
    const taxExistingReliefs = document.getElementById("tax-existing-reliefs");
    const taxDonations = document.getElementById("tax-donations");
    const relItems = Array.from(document.querySelectorAll(".rel-item"));

    // Pre-existing reliefs are now itemised; auto-sum them applying statutory caps.
    function computePreExistingReliefs() {
        const cpfEmpVal = Math.max(0, parseFloat(document.getElementById("rel-cpf-emp")?.value) || 0);
        const wmcrVal = Math.max(0, parseFloat(document.getElementById("rel-wmcr")?.value) || 0);
        const childVal = Math.max(0, parseFloat(document.getElementById("rel-child")?.value) || 0);
        const parentVal = Math.max(0, parseFloat(document.getElementById("rel-parent")?.value) || 0);
        const nsmanVal = Math.max(0, parseFloat(document.getElementById("rel-nsman")?.value) || 0);
        const rawLifeVal = Math.max(0, parseFloat(document.getElementById("rel-life")?.value) || 0);
        const cpfCashVal = Math.max(0, parseFloat(document.getElementById("rel-cpf-cash")?.value) || 0);
        const srsVal = Math.max(0, parseFloat(document.getElementById("rel-srs")?.value) || 0);
        const earnedVal = Math.max(0, parseFloat(document.getElementById("rel-earned")?.value) || 0);
        const otherVal = Math.max(0, parseFloat(document.getElementById("rel-other")?.value) || 0);

        // Life Insurance Relief Cap: Max is lower of actual premiums or (S$5,000 - CPF Employee contributions)
        const allowedLifeRelief = Math.min(rawLifeVal, Math.max(0, 5000 - cpfEmpVal));

        // Let's dynamically update a visual label or style for life insurance to inform the user if it's capped
        const relLife = document.getElementById("rel-life");
        if (relLife) {
            const lifeCap = Math.max(0, 5000 - cpfEmpVal);
            if (rawLifeVal > lifeCap) {
                relLife.style.borderColor = "var(--primary)";
                relLife.title = `Capped at S$${lifeCap.toLocaleString()} due to S$5,000 ceiling minus CPF Employee contributions`;
            } else {
                relLife.style.borderColor = "var(--border)";
                relLife.title = "";
            }
        }

        const sum = cpfEmpVal + wmcrVal + childVal + parentVal + nsmanVal + allowedLifeRelief + cpfCashVal + srsVal + earnedVal + otherVal;
        if (taxExistingReliefs) taxExistingReliefs.textContent = "S$" + sum.toLocaleString();
        return sum;
    }

    // Always-visible card shows ONLY the effective tier (single highlighted band row),
    // so it doesn't duplicate the full progressive schedule rendered inside the Optimize results.
    const taxTierEffectiveRow = document.getElementById("tax-tier-effective-row");
    const taxTierEffectiveRate = document.getElementById("tax-tier-effective-rate");
    function renderEffectiveTier() {
        if (!taxTierEffectiveRow) return;
        const income = Math.max(0, parseFloat(taxAssessableIncome.value) || 0);
        const preExisting = Math.max(0, computePreExistingReliefs());
        const donations = Math.max(0, parseFloat(taxDonations.value) || 0);
        // Match the optimizer: donations reduce chargeable income at face value (the 2.5x
        // multiplier only governs the separate donation tax-saving figure, not the band).
        const chargeable = Math.max(0, income - preExisting - donations);

        if (chargeable <= 0) {
            taxTierEffectiveRow.innerHTML = `<tr><td colspan="2" style="padding:8px; font-size:11.5px; color:var(--text-subtle); text-align:center;">Enter your income &amp; reliefs to see your tier…</td></tr>`;
            if (taxTierEffectiveRate) taxTierEffectiveRate.textContent = "";
            return;
        }

        let lower = 0, band = "", bandRate = 0, marginalRate = 0;
        for (let i = 0; i < TAX_BRACKETS.length; i++) {
            const b = TAX_BRACKETS[i];
            const upper = b.limit === Infinity ? null : lower + b.limit;
            if (chargeable > lower && (upper === null || chargeable <= upper)) {
                band = i === 0 ? "First S$" + lower.toLocaleString() + (upper ? "–S$" + upper.toLocaleString() : "")
                    : "S$" + (lower + 1).toLocaleString() + (upper ? " – S$" + upper.toLocaleString() : "+");
                bandRate = b.rate * 100;
                marginalRate = bandRate;
                break;
            }
            if (upper === null) break;
            lower = upper;
        }

        const tax = calculateSingaporeTax(chargeable);
        const effRate = (tax / chargeable) * 100;
        taxTierEffectiveRow.innerHTML = `
            <tr style="background:#fff7ed; font-weight:700;">
                <td style="padding:6px 8px; border-bottom:1px solid var(--border); font-size:12px; color:var(--text-main);">${band}</td>
                <td style="padding:6px 8px; border-bottom:1px solid var(--border); font-size:12px; text-align:right; color:var(--text-main);">${bandRate.toFixed(1)}%</td>
            </tr>`;
        if (taxTierEffectiveRate) taxTierEffectiveRate.innerHTML = `Effective: <strong style="color:var(--text-main);">${effRate.toFixed(2)}%</strong> · Marginal: <strong style="color:var(--text-main);">${marginalRate.toFixed(1)}%</strong> · Chargeable: <strong style="color:var(--text-main);">S$${chargeable.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>`;
    }
    relItems.forEach(inp => inp.addEventListener("input", renderEffectiveTier));
    if (taxDonations) taxDonations.addEventListener("input", renderEffectiveTier);
    if (taxAssessableIncome) taxAssessableIncome.addEventListener("input", renderEffectiveTier);
    renderEffectiveTier();
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

    // CPF HDB Accrued Interest Calculator binding
    const cpfIntPrincipal = document.getElementById("cpf-interest-principal");
    const cpfIntDuration = document.getElementById("cpf-interest-duration");
    const cpfIntBtn = document.getElementById("calc-cpf-interest-btn");
    const cpfIntResult = document.getElementById("cpf-interest-result");

    if (cpfIntBtn && cpfIntPrincipal && cpfIntDuration && cpfIntResult) {
        cpfIntBtn.addEventListener("click", () => {
            const principal = parseFloat(cpfIntPrincipal.value);
            const duration = parseFloat(cpfIntDuration.value);

            if (isNaN(principal) || principal <= 0 || isNaN(duration) || duration <= 0) {
                cpfIntResult.innerHTML = "<span style='color:var(--text-error); font-weight:700;'>⚠️ Please enter positive values for Principal and Duration.</span>";
                return;
            }

            // Ordinary Account rate is 2.5% compounded annually
            const rate = 0.025;
            const totalRefund = principal * Math.pow(1 + rate, duration);
            const accruedInterest = totalRefund - principal;

            cpfIntResult.innerHTML = `
                <div style="background:var(--bg-panel); border:1px solid var(--border); padding:14px; border-radius:8px; display:flex; flex-direction:column; gap:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:12px; font-weight:700; color:var(--text-muted);">Total CPF Refund Required:</span>
                        <span style="font-size:16px; font-weight:800; color:var(--text-main);">S$${totalRefund.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; border-top:1px dashed var(--border); padding-top:6px;">
                        <span style="color:var(--text-muted);">Principal Used:</span>
                        <span style="font-weight:600; color:var(--text-main);">S$${principal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px;">
                        <span style="color:var(--text-muted);">Accrued Interest (2.5% Compounded):</span>
                        <span style="font-weight:700; color:#ef4444;">S$${accruedInterest.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                    <div style="font-size:11px; color:var(--text-muted); line-height:1.4; border-top:1px solid var(--border); padding-top:8px; margin-top:4px;">
                        <i class="fa-solid fa-circle-info" style="color:var(--primary);"></i> <strong>Note:</strong> When selling your HDB flat, this total refund amount is returned from sale proceeds directly back to your own CPF OA. It is **not a fee or penalty paid to the government**; it restores your own retirement balance. 
                        <br><br>
                        <em>Safeguard:</em> If the sale proceeds (at market value) are insufficient to cover this refund, you do not have to top up cash. The shortfall is written off by CPF.
                    </div>
                </div>
            `;
        });
    }

    const loadedSgHubPanes = {
        "hub-transport-pane": false,
        "hub-gov-transit-pane": false,
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

    // "Transit & Transport" and "Gov Updates" are two separate tabs with their own backend
    // endpoints — the transport tab fetches LTA/COE/ICA only (/api/sg-hub/transit); the Gov
    // Updates tab fetches Telegram broadcasts + PUB flood alerts only (/api/sg-hub/gov-updates).
    // Each tab loads its own data so neither waits on the other's (slower) sources.

    async function loadSgHubPaneData(paneId) {
        if (loadedSgHubPanes[paneId]) return;

        let endpoint = "";
        if (paneId === "hub-transport-pane") endpoint = "/api/sg-hub/transit";
        else if (paneId === "hub-gov-transit-pane") endpoint = "/api/sg-hub/gov-updates";
        else if (paneId === "hub-hdb-pane") endpoint = "/api/sg-hub/hdb";
        else if (paneId === "hub-jobs-pane") endpoint = "/api/sg-hub/jobs?sector=tech";
        else if (paneId === "hub-community-pane") endpoint = "/api/sg-hub/community";
        else if (paneId === "hub-env-pane") endpoint = "/api/sg-hub/weather";
        else if (paneId === "hub-tax-pane") endpoint = "/api/sg-hub/tax";

        if (!endpoint) return;

        // The Occupational Wage Explorer has its own (heavier, Excel-backed) endpoint — kick it
        // off in parallel with the main jobs fetch; it caches itself under its own key.
        if (paneId === "hub-jobs-pane") loadOccupationalWages();

        showPaneLoader(paneId);

        try {
            const res = await fetch(endpoint);
            if (!res.ok) throw new Error("API error fetching pane " + paneId);
            const data = await res.json();

            if (paneId === "hub-transport-pane") {
                renderTransitPane(data);
            } else if (paneId === "hub-gov-transit-pane") {
                renderGovUpdatesPane(data);
            } else if (paneId === "hub-hdb-pane") {
                renderHdbPane(data);
            } else if (paneId === "hub-jobs-pane") {
                renderJobsPane(data);
            } else if (paneId === "hub-community-pane") {
                renderCommunityPane(data);
            } else if (paneId === "hub-env-pane") {
                renderWeatherPane(data);
            } else if (paneId === "hub-tax-pane") {
                renderTaxPane(data);
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

    function renderTaxPane(data) {
        if (!taxDeadlinesContent) return;

        // Populate limits fetched dynamically
        if (data.limits) {
            if (taxCpfCap) taxCpfCap.value = data.limits.cpf_sa_rstu_max;
            if (taxSrsCap) {
                const isForeigner = taxResidencyStatus ? taxResidencyStatus.value === "foreigner" : false;
                const srsLimit = isForeigner ? data.limits.srs_foreigner_max : data.limits.srs_citizen_pr_max;
                taxSrsCap.value = srsLimit;
                if (taxSrsCapHint) {
                    taxSrsCapHint.textContent = isForeigner
                        ? `SRS yearly relief cap (S$${srsLimit.toLocaleString()} Foreigner)`
                        : `SRS yearly relief cap (S$${srsLimit.toLocaleString()} Citizen/PR)`;
                }
            }
        }

        // --- Render IRAS Due Dates Timeline ---
        const banner = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
            <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${getRetrievalTimestamp()}
        </div>`;

        let timelineHtml = "";
        if (data.due_dates && data.due_dates.length > 0) {
            timelineHtml += `<div style="display:flex; flex-direction:column; gap:10px;">`;
            data.due_dates.forEach(item => {
                const isIIT = item.category.toLowerCase().includes("individual");
                const borderLeft = isIIT ? "4px solid #ef4444" : "1px solid var(--border)";
                const bg = isIIT ? "#fef2f2" : "var(--bg-muted)";
                const badgeBg = isIIT ? "#fee2e2" : "var(--border)";
                const badgeColor = isIIT ? "#b91c1c" : "var(--text-main)";

                timelineHtml += `<div style="background:${bg}; border:1px solid var(--border); border-left:${borderLeft}; border-radius:8px; padding:12px; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
                    <div style="display:flex; flex-direction:column; gap:4px; max-width:80%;">
                        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                            <span style="font-weight:700; color:var(--text-main); font-size:13.5px;">${escapeHTML(item.date)}</span>
                            <span style="background:${badgeBg}; color:${badgeColor}; font-size:10px; font-weight:700; padding:2px 7px; border-radius:4px; text-transform:uppercase; letter-spacing:0.5px;">${escapeHTML(item.category)}</span>
                        </div>
                        <span style="color:var(--text-muted); font-size:12.5px; line-height:1.4;">${escapeHTML(item.label)}</span>
                    </div>
                    <a href="${safeURL(item.link)}" target="_blank" style="background:#ffffff; border:1px solid var(--border); padding:6px 12px; border-radius:6px; font-size:12px; color:var(--link); text-decoration:none; font-weight:600; display:inline-flex; align-items:center; gap:5px;">
                        File Now <i class="fa-solid fa-up-right-from-square" style="font-size:10px;"></i>
                    </a>
                </div>`;
            });
            timelineHtml += `</div>`;
        } else {
            timelineHtml = `<p style="color: var(--text-subtle); margin: 0; font-style: italic;">No tax deadlines reported.</p>`;
        }
        taxDeadlinesContent.innerHTML = banner + timelineHtml;

        // Brackets are now defined globally at the top of app.js to prevent early reference errors
        // calculateSingaporeTax is also defined globally.

        // --- Auto-sync SRS cap when residency changes ---
        if (taxResidencyStatus && taxSrsCap) {
            taxResidencyStatus.addEventListener("change", () => {
                const isForeigner = taxResidencyStatus.value === "foreigner";
                const srsLimit = data.limits ? (isForeigner ? data.limits.srs_foreigner_max : data.limits.srs_citizen_pr_max) : (isForeigner ? 35700 : 15300);
                taxSrsCap.value = srsLimit;
                if (taxSrsCapHint) {
                    taxSrsCapHint.textContent = isForeigner
                        ? `SRS yearly relief cap (S$${srsLimit.toLocaleString()} Foreigner)`
                        : `SRS yearly relief cap (S$${srsLimit.toLocaleString()} Citizen/PR)`;
                }
            });
        }

        // --- Optimizer Form Listener ---
        if (calcTaxOptBtn) {
            // Remove any old event listeners to avoid duplicates
            const newBtn = calcTaxOptBtn.cloneNode(true);
            calcTaxOptBtn.parentNode.replaceChild(newBtn, calcTaxOptBtn);

            newBtn.addEventListener("click", () => {
                const income = parseFloat(taxAssessableIncome.value) || 0;
                const budget = parseFloat(taxTopupBudget.value) || 0;
                const isForeigner = taxResidencyStatus.value === "foreigner";

                if (income <= 0 || budget <= 0) {
                    alert("Please enter a valid positive Assessable Income and Top-up Budget.");
                    return;
                }

                // Read statutory relief caps (shown as labels now, read textContent)
                const maxCPFReliefSelf = Math.max(0, parseFloat(taxCpfCap.textContent.replace(/,/g, '')) || 0);
                const maxSRSRelief = Math.max(0, parseFloat(taxSrsCap.textContent.replace(/,/g, '')) || 0);

                // --- S$80,000 total personal relief cap (effective YA 2018+) ---
                const RELIEF_CAP = 80000;
                const preExisting = Math.max(0, computePreExistingReliefs());
                const headroom = Math.max(0, RELIEF_CAP - preExisting);

                // Optimal split algorithm:
                // 1. CPF SA/MA (RSTU) first up to its cap (highest risk-free interest 4.08%)
                // 2. SRS up to its cap
                // 3. Excess budget goes to "unused"
                let cpfAlloc = Math.min(budget, maxCPFReliefSelf);
                let remainingBudget = budget - cpfAlloc;
                let srsAlloc = Math.min(remainingBudget, maxSRSRelief);

                let totalDeductible = cpfAlloc + srsAlloc;
                let unusedBudget = budget - totalDeductible;

                // Only the portion of new top-ups that fits inside the remaining relief
                // cap actually reduces taxable income; the rest is "capped out" (no tax saving).
                const effectiveDeduction = Math.min(totalDeductible, headroom);
                const cappedOut = Math.max(0, (preExisting + totalDeductible) - RELIEF_CAP);

                // Chargeable income the optimization acts on (assessable less pre-existing
                // reliefs AND donations — donations are a separate deduction, not a relief,
                // so they reduce taxable income but do NOT consume the S$80k relief cap).
                const donations = Math.max(0, parseFloat(taxDonations.value) || 0);
                const referenceIncome = Math.max(0, income - preExisting - donations);

                // Calculate taxes
                // Note: referenceIncome already excludes donations (2.5x deduction applied above)
                let originalTaxNoDonation = calculateSingaporeTax(Math.max(0, income - preExisting));
                let originalTax = calculateSingaporeTax(referenceIncome);
                let optimizedChargeableIncome = Math.max(0, referenceIncome - effectiveDeduction);
                let optimizedTax = calculateSingaporeTax(optimizedChargeableIncome);
                let totalSaved = Math.max(0, originalTax - optimizedTax);
                // Donation tax saving = tax without donations - tax with donations applied
                const donationDeduction = donations * 2.5;
                const donationTaxSaving = Math.max(0, originalTaxNoDonation - originalTax);

                // --- Effective & Marginal Rate (on chargeable income) ---
                const effRate = referenceIncome > 0 ? (originalTax / referenceIncome) * 100 : 0;
                let marginalRate = 0;
                {
                    let acc = 20000, found = false;
                    for (let i = 1; i < TAX_BRACKETS.length; i++) {
                        const b = TAX_BRACKETS[i];
                        if (referenceIncome <= acc + b.limit) { marginalRate = b.rate * 100; found = true; break; }
                        acc += b.limit;
                        if (found) break;
                    }
                }

                // --- Progressive Tax Tier Table (rendered from the same bracket data the engine uses) ---
                const fmtMoney = (n) => "S$" + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                let tierRows = "";
                {
                    let lower = 0;
                    for (let i = 0; i < TAX_BRACKETS.length; i++) {
                        const b = TAX_BRACKETS[i];
                        const upper = b.limit === Infinity ? null : lower + b.limit;
                        const band = i === 0
                            ? "First S$" + lower + (upper ? "–" + (upper).toLocaleString() : "")
                            : "S$" + (lower + 1).toLocaleString() + (upper ? " – S$" + upper.toLocaleString() : "+");
                        const inBand = referenceIncome > lower && (upper === null || referenceIncome <= upper);
                        const ratePct = (b.rate * 100).toFixed(1);
                        tierRows += `
                            <tr style="${inBand ? 'background:#fff7ed; font-weight:700;' : ''}">
                                <td style="padding:6px 8px; border-bottom:1px solid var(--border); font-size:11.5px; color:var(--text-main);">${band}</td>
                                <td style="padding:6px 8px; border-bottom:1px solid var(--border); font-size:11.5px; text-align:right; color:var(--text-main);">${ratePct}%</td>
                                ${i === 0 ? `<td style="padding:6px 8px; border-bottom:1px solid var(--border); font-size:11px; color:var(--text-muted);" colspan="2">Tax-free threshold</td>` : ''}
                            </tr>`;
                        if (upper === null) break;
                        lower = upper;
                    }
                }
                const taxTierTableHtml = `
                    <div style="background:var(--bg-muted); border:1px solid var(--border); border-radius:8px; padding:12px 14px; margin-bottom:20px;">
                        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px;">
                            <span style="font-size:12px; font-weight:700; color:var(--text-main); text-transform:uppercase; letter-spacing:0.5px;"><i class="fa-solid fa-table-list"></i> Progressive Tax Tiers (YA 2026)</span>
                            <span style="font-size:11px; color:var(--text-muted);">Effective: <strong style="color:var(--text-main);">${effRate.toFixed(2)}%</strong> · Marginal: <strong style="color:var(--text-main);">${marginalRate.toFixed(1)}%</strong></span>
                        </div>
                        <table style="width:100%; border-collapse:collapse;">
                            <thead>
                                <tr>
                                    <th style="text-align:left; font-size:10.5px; text-transform:uppercase; color:var(--text-muted); padding:4px 8px; border-bottom:2px solid var(--border);">Chargeable Income Band</th>
                                    <th style="text-align:right; font-size:10.5px; text-transform:uppercase; color:var(--text-muted); padding:4px 8px; border-bottom:2px solid var(--border);">Rate</th>
                                </tr>
                            </thead>
                            <tbody>${tierRows}</tbody>
                        </table>
                    </div>`;

                // --- Progressive Bracket Targeter ---
                const thresholds = [
                    { value: 1000000, rate: 0.24, nextRate: 0.23 },
                    { value: 500000, rate: 0.23, nextRate: 0.22 },
                    { value: 320000, rate: 0.22, nextRate: 0.20 },
                    { value: 280000, rate: 0.20, nextRate: 0.195 },
                    { value: 240000, rate: 0.195, nextRate: 0.19 },
                    { value: 200000, rate: 0.19, nextRate: 0.18 },
                    { value: 160000, rate: 0.18, nextRate: 0.15 },
                    { value: 120000, rate: 0.15, nextRate: 0.115 },
                    { value: 80000, rate: 0.115, nextRate: 0.07 },
                    { value: 40000, rate: 0.07, nextRate: 0.035 },
                    { value: 30000, rate: 0.035, nextRate: 0.02 },
                    { value: 20000, rate: 0.02, nextRate: 0.00 }
                ];

                let currentThreshold = null;
                for (let t of thresholds) {
                    if (referenceIncome > t.value) {
                        currentThreshold = t;
                        break;
                    }
                }

                let bracketAdvisoryHtml = "";
                if (currentThreshold) {
                    const amountToDrop = referenceIncome - currentThreshold.value;
                    const marginalRatePct = (currentThreshold.rate * 100).toFixed(1);
                    const lowerRatePct = (currentThreshold.nextRate * 100).toFixed(1);

                    if (totalDeductible >= amountToDrop) {
                        const taxSavedOnThisBracket = amountToDrop * currentThreshold.rate;
                        bracketAdvisoryHtml = `
                            <div style="background:#f0fdf4; border:1px solid #bbf7d0; padding:14px; border-radius:8px; margin-bottom:20px; border-left:4px solid #16a34a;">
                                <span style="font-weight:700; color:#15803d; font-size:12.5px; display:block; margin-bottom:4px;">
                                    <i class="fa-solid fa-circle-check"></i> Marginal Tax Tier Drop Successful!
                                </span>
                                <span style="font-size:12px; color:#166534; line-height:1.45; display:block;">
                                    By topping up S$${totalDeductible.toLocaleString()}, you successfully reduced your chargeable income below the **S$${currentThreshold.value.toLocaleString()}** threshold. This drops you from the **${marginalRatePct}%** tax tier into the **${lowerRatePct}%** tier, saving you **S$${taxSavedOnThisBracket.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}** on this bracket portion alone!
                                </span>
                            </div>
                        `;
                    } else {
                        const shortfall = amountToDrop - totalDeductible;
                        const potentialExtraSaving = shortfall * currentThreshold.rate;
                        const maxPossibleTopup = maxCPFReliefSelf + maxSRSRelief;

                        let tipMessage = "";
                        if (amountToDrop <= maxPossibleTopup) {
                            tipMessage = `Topping up an additional **S$${shortfall.toLocaleString()}** (total S$${amountToDrop.toLocaleString()}) will drop your chargeable income below **S$${currentThreshold.value.toLocaleString()}**, escaping the **${marginalRatePct}%** tax rate on those dollars and saving you an additional **S$${potentialExtraSaving.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}**!`;
                        } else {
                            tipMessage = `To drop below the **S$${currentThreshold.value.toLocaleString()}** threshold requires a top-up of **S$${amountToDrop.toLocaleString()}**, which exceeds the annual CPF + SRS tax relief ceiling of **S$${maxPossibleTopup.toLocaleString()}** for this year.`;
                        }

                        bracketAdvisoryHtml = `
                            <div style="background:#fffbeb; border:1px solid #fef3c7; padding:14px; border-radius:8px; margin-bottom:20px; border-left:4px solid #d97706;">
                                <span style="font-weight:700; color:#b45309; font-size:12.5px; display:block; margin-bottom:4px;">
                                    <i class="fa-solid fa-lightbulb"></i> Next Tax Tier Target: S$${currentThreshold.value.toLocaleString()}
                                </span>
                                <span style="font-size:12px; color:#92400e; line-height:1.45; display:block;">
                                    You are in the progressive **${marginalRatePct}%** tax tier. ${tipMessage}
                                </span>
                            </div>
                        `;
                    }
                }

                // Build results HTML
                let savingsBoxHtml;
                const reducedNote = cappedOut > 0
                    ? `You reduced your taxable income by <strong>S$${effectiveDeduction.toLocaleString()}</strong> (S$${cappedOut.toLocaleString()} of your S$${totalDeductible.toLocaleString()} top-up is capped out at the S$80,000 relief limit).`
                    : `You reduced your taxable income by <strong>S$${effectiveDeduction.toLocaleString()}</strong>!`;
                if (originalTax === 0) {
                    savingsBoxHtml = `
                    <div style="background:#eafaf1; border: 1px solid #a3d9b1; padding:16px; border-radius:10px; margin-bottom:20px; text-align:center;">
                        <span style="font-size:12px; font-weight:700; color:#1a7f3c; text-transform:uppercase; letter-spacing:0.5px; display:block; margin-bottom:4px;">Estimated Tax Savings</span>
                        <span style="font-size:32px; font-weight:900; color:#1a7f3c; display:block; margin-bottom:6px;">S$${totalSaved.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        <p style="margin:0; font-size:12.5px; color:#1b5e20; font-weight:600;">Your chargeable income of S$${referenceIncome.toLocaleString()} (assessable S$${income.toLocaleString()} less S$${preExisting.toLocaleString()} existing reliefs${donations > 0 ? ` and S$${donations.toLocaleString()} donations` : ""}) is within the <strong>S$20,000 tax-free threshold</strong>, so you currently owe <strong>S$0</strong> income tax. The top-up still grows your retirement (CPF SA + SRS) even with no immediate tax saving.</p>
                    </div>`;
                } else {
                    savingsBoxHtml = `
                    <div style="background:#eafaf1; border: 1px solid #a3d9b1; padding:16px; border-radius:10px; margin-bottom:20px; text-align:center;">
                        <span style="font-size:12px; font-weight:700; color:#1a7f3c; text-transform:uppercase; letter-spacing:0.5px; display:block; margin-bottom:4px;">Estimated Tax Savings</span>
                        <span style="font-size:32px; font-weight:900; color:#1a7f3c; display:block; margin-bottom:6px;">S$${totalSaved.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        <p style="margin:0; font-size:12.5px; color:#1b5e20; font-weight:600;">${reducedNote}</p>
                    </div>`;
                }

                // Relief-cap status strip (only when part of the top-up is capped out)
                let capStatusHtml = "";
                if (cappedOut > 0) {
                    capStatusHtml = `
                    <div style="background:#fffbeb; border:1px solid #fef3c7; border-left:4px solid #d97706; padding:12px 14px; border-radius:8px; margin-bottom:16px; font-size:12px; color:#92400e; line-height:1.45;">
                        <i class="fa-solid fa-triangle-exclamation"></i> <strong>Relief cap reached (S$80,000 YA limit):</strong> Total reliefs now claimed = <strong>S$${(preExisting + effectiveDeduction).toLocaleString()}</strong> (S$${preExisting.toLocaleString()} existing + S$${effectiveDeduction.toLocaleString()} from this top-up). <strong>S$${cappedOut.toLocaleString()}</strong> of your top-up exceeded the cap and yields <strong>no extra tax saving</strong> — though the cash still goes into CPF SA / SRS for retirement.
                    </div>`;
                }

                let resultsHtml = `
                    ${bracketAdvisoryHtml}
                    ${taxTierTableHtml}
                    ${capStatusHtml}
                    ${savingsBoxHtml}

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:20px;">
                        <div style="background:var(--bg-muted); border:1px solid var(--border); padding:12px; border-radius:8px; text-align:center;">
                            <span style="font-size:11px; color:var(--text-muted); display:block; margin-bottom:4px;">Original Tax Payable</span>
                            <span style="font-size:16px; font-weight:700; color:var(--text-main);">S$${originalTax.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        </div>
                        <div style="background:var(--bg-muted); border:1px solid var(--border); padding:12px; border-radius:8px; text-align:center;">
                            <span style="font-size:11px; color:var(--text-muted); display:block; margin-bottom:4px;">Optimized Tax Payable</span>
                            <span style="font-size:16px; font-weight:700; color:var(--text-main);">S$${optimizedTax.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        </div>
                    </div>

                    <h4 style="font-size:13px; font-weight:700; margin-bottom:10px; color:var(--text-main); text-transform:uppercase; letter-spacing:0.5px;"><i class="fa-solid fa-list-check"></i> Recommended Allocation Split</h4>
                    <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:20px;">
                        
                        <!-- CPF SA RSTU Topup Card -->
                        <div style="background:#f0f7ff; border:1px solid #b3d7ff; border-left:4px solid #005EC4; padding:12px; border-radius:8px; display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-weight:700; font-size:13px; color:#004085; display:block;">CPF Special Account (RSTU) Top-up</span>
                                <span style="font-size:11px; color:#004085; line-height:1.3;">Retirement Account compound growth (4.08% guaranteed yield)</span>
                            </div>
                            <span style="font-weight:800; font-size:16px; color:#004085;">S$${cpfAlloc.toLocaleString()}</span>
                        </div>

                        <!-- SRS Contribution Card -->
                        <div style="background:#fbf2ff; border:1px solid #e1bbfd; border-left:4px solid #a855f7; padding:12px; border-radius:8px; display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-weight:700; font-size:13px; color:#6b21a8; display:block;">Supplementary Retirement Scheme (SRS)</span>
                                <span style="font-size:11px; color:#6b21a8; line-height:1.3;">Investable cash account (flexible shares/bonds/annuity purchase)</span>
                            </div>
                            <span style="font-weight:800; font-size:16px; color:#6b21a8;">S$${srsAlloc.toLocaleString()}</span>
                        </div>


                        ${donations > 0 ? `
                        <!-- Donation Deduction Card -->
                        <div style="background:#f0fdf4; border:1px solid #bbf7d0; border-left:4px solid #16a34a; padding:12px; border-radius:8px; display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-weight:700; font-size:13px; color:#15803d; display:block;"><i class="fa-solid fa-heart"></i> IPC-Approved Donations (2.5× Deduction)</span>
                                <span style="font-size:11px; color:#166534; line-height:1.3;">S$${donations.toLocaleString()} donated → S$${donationDeduction.toLocaleString(undefined, { minimumFractionDigits: 0 })} deducted from chargeable income (outside S$80k cap)</span>
                            </div>
                            <div style="text-align:right; flex-shrink:0; margin-left:12px;">
                                <span style="font-weight:800; font-size:16px; color:#15803d; display:block;">−S$${donationTaxSaving.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                                <span style="font-size:10px; color:#166534;">tax saved</span>
                            </div>
                        </div>` : ''}

                        ${unusedBudget > 0 ? `
                        <!-- Unused Excess Card -->
                        <div style="background:#fffbeb; border:1px solid #fef3c7; border-left:4px solid #d97706; padding:12px; border-radius:8px; display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-weight:700; font-size:13px; color:#92400e; display:block;">Unused Excess Budget</span>
                                <span style="font-size:11px; color:#92400e; line-height:1.3;">This S$${unusedBudget.toLocaleString()} exceeds the relief limits for YA 2026. Keep in savings.</span>
                            </div>
                            <span style="font-weight:800; font-size:16px; color:#92400e;">S$${unusedBudget.toLocaleString()}</span>
                        </div>
                        ` : ''}
                    </div>

                    <!-- Trade-off Advisory Box -->
                    <div style="background:#f8fafc; border:1px solid var(--border); border-radius:8px; padding:14px; font-size:12px; line-height:1.5; color:var(--text-main);">
                        <strong style="display:block; margin-bottom:6px; color:var(--text-main); font-size:12.5px;"><i class="fa-solid fa-circle-info" style="color:var(--primary);"></i> Important Liquidity &amp; Asset Advisory:</strong>
                        <ul style="margin:0; padding-left:16px; display:flex; flex-direction:column; gap:6px;">
                            <li><strong>CPF SA Top-ups (RSTU)</strong> are <strong>irreversible</strong>. The cash is permanently transferred and locked until age 55, earning a guaranteed base rate of 4.08% per annum.</li>
                            <li><strong>SRS Contributions</strong> are flexible. You can invest these in Singapore bonds, blue-chip shares, or annuity plans. However, early cash withdrawals before statutory retirement age trigger a <strong>5% penalty</strong> and are taxed 100%. Post-retirement withdrawals are <strong>50% tax-free</strong>.</li>
                        </ul>
                    </div>
                `;

                taxOptimizerResults.innerHTML = resultsHtml;
                taxOptimizerResults.classList.remove("hidden");
            });
        }
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
            <div style="margin-bottom: 16px;">
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

    function renderTransportPane(taxiAvailability, coe, coeHistory) {
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
                    ${c.momentum ? `<div style="font-size: 10px; color: var(--text-muted); margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border);">📶 ${escapeHTML(c.momentum)}</div>` : ''}
                </div>`).join('')
            : `<p style="color: var(--text-subtle); margin:0; font-size: 13px;">COE data unavailable.</p>`;

        const hasCoeHistory = coeHistory && coeHistory.exercises && coeHistory.exercises.length > 1;
        const coeCaption = (coeHistory && coeHistory.insight)
            ? coeHistory.insight
            : "Two bidding rounds per month — hover for every category's exact premium.";
        const coeHistoryHtml = hasCoeHistory ? `
            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin: 2px 0 8px;">📈 COE Premium Trend — Last ${coeHistory.exercises.length} Exercises</div>
            <div id="coe-trend-chart" style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 10px 10px 4px;"></div>
            <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;">💡 ${escapeHTML(coeCaption)}</div>
        ` : '';

        const taxiMapHtml = taxiAvailability ? `
            <div style="margin-bottom: 14px;">
                <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">🗺️ Live Taxi Positions — ${taxiAvailability.count.toLocaleString()} available islandwide</div>
                <div id="taxi-map" style="height: 280px; border-radius: 10px; border: 1px solid var(--border); position: relative; z-index: 1;"></div>
                <div style="font-size: 10.5px; color: var(--text-muted); margin-top: 5px;">Showing up to 500 sampled positions · Source: LTA DataMall · ${escapeHTML(taxiAvailability.retrieved_at)}</div>
            </div>` : '';

        transportContent.innerHTML = banner + `
            <div style="background: var(--bg-panel); border: 1px solid var(--border); border-radius: 10px; padding: 14px; margin-bottom: 16px;">
                <span style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 8px;">🚗 COE BIDDING — ${coe ? escapeHTML(coe.exercise) : 'N/A'}</span>
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: ${hasCoeHistory ? '14px' : '0'};">
                    ${coeCategoriesHtml}
                </div>
                ${coeHistoryHtml}
            </div>
            <div style="background: var(--bg-panel); border: 1px solid var(--border); border-radius: 10px; padding: 14px;">
                <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: ${taxiMapHtml ? '14px' : '0'};">
                    ${taxiHtml}
                </div>
                ${taxiMapHtml}
            </div>
        `;

        if (hasCoeHistory) {
            renderLineChart(document.getElementById("coe-trend-chart"), {
                xLabels: coeHistory.exercises,
                series: ["A", "B", "C", "D", "E"].map(c => ({
                    name: `Cat ${c}`,
                    color: coeCategoryColors[c],
                    values: coeHistory.categories[c],
                })),
                xTickEvery: 8,
            });
        }

        // Render taxi dot-density map
        if (window.taxiMap) { try { window.taxiMap.remove(); } catch (e) { } window.taxiMap = null; }
        try {
            const taxiMapEl = document.getElementById("taxi-map");
            const positions = taxiAvailability && taxiAvailability.sample_positions;
            if (taxiMapEl && typeof L === "undefined") {
                // Leaflet failed to load from its CDN (e.g. blocked/stalled network) — the div
                // would otherwise stay blank forever with no indication anything went wrong.
                taxiMapEl.innerHTML = "<div style='display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:12px;text-align:center;padding:0 16px;'>⚠️ Map library failed to load (check your network connection), positions unavailable.</div>";
            } else if (taxiMapEl && (!positions || positions.length === 0)) {
                taxiMapEl.innerHTML = "<div style='display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:12px;'>No taxi position data available right now.</div>";
            } else if (taxiMapEl) {
                const tmap = L.map(taxiMapEl, { zoomControl: true, scrollWheelZoom: false })
                    .setView([1.3521, 103.8198], 11);
                window.taxiMap = tmap;
                window.taxiUserMarker = null;
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 18,
                    attribution: '© OpenStreetMap'
                }).addTo(tmap);
                positions.forEach(([lat, lon]) => {
                    L.circleMarker([lat, lon], {
                        radius: 4,
                        color: '#ffffff',
                        weight: 1,
                        fillColor: '#f59e0b',
                        fillOpacity: 0.9
                    }).addTo(tmap);
                });
            }
        } catch (e) {
            console.error("Failed to render taxi map:", e);
            const taxiMapEl = document.getElementById("taxi-map");
            if (taxiMapEl) taxiMapEl.innerHTML = "<div style='display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:12px;'>⚠️ Couldn't render the map.</div>";
        }

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

    function showUserLocationOnTaxiMap(lat, lon) {
        const tmap = window.taxiMap;
        if (!tmap) return;
        if (window.taxiUserMarker) { try { tmap.removeLayer(window.taxiUserMarker); } catch (e) { } }
        window.taxiUserMarker = L.circleMarker([lat, lon], {
            radius: 8,
            color: '#ffffff',
            weight: 2,
            fillColor: '#2563eb',
            fillOpacity: 1
        }).addTo(tmap).bindTooltip("You are here", { permanent: false, direction: "top" });
        // animate:false — Leaflet's animated setView doesn't reliably persist in this app's
        // layout (likely a CSS transition conflict from an ancestor), leaving the map visually
        // stuck at its old center/zoom even though the marker itself is placed correctly.
        tmap.setView([lat, lon], 14, { animate: false });
    }

    function resetTaxiMapView() {
        const tmap = window.taxiMap;
        if (!tmap) return;
        if (window.taxiUserMarker) { try { tmap.removeLayer(window.taxiUserMarker); } catch (e) { } window.taxiUserMarker = null; }
        tmap.setView([1.3521, 103.8198], 11, { animate: false });
    }

    function bindTaxiButtons(taxiAvailability) {
        const block = document.getElementById("taxi-stat-block");
        const aroundBtn = document.getElementById("taxi-around-you-btn");
        const showAllBtn = document.getElementById("taxi-show-all-btn");

        if (showAllBtn) {
            showAllBtn.addEventListener("click", () => {
                if (block) block.innerHTML = islandwideTaxiHtml(taxiAvailability);
                resetTaxiMapView();
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
                showUserLocationOnTaxiMap(loc.lat, loc.lon);
                bindTaxiButtons(taxiAvailability);
            } catch (err) {
                aroundBtn.disabled = false;
                aroundBtn.innerHTML = originalLabel;
                showTaxiError(block, "Couldn't fetch nearby taxis. Try again.");
            }
        });
    }

    function renderTransitPane(data) {
        renderTransportPane(data.taxi_availability, data.coe, data.coe_history);

        const banner = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
            <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${getRetrievalTimestamp()}
        </div>`;

        // --- ICA Newsroom Advisories (fetched for this tab's ICA card) ---
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

        // ── Transit section: LTA DataMall structured view OR key-not-configured notice ──
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
                const statusColor = isDisrupted ? "#c0392b" : "#1a7f3c";
                const statusBg = isDisrupted ? "#fdecea" : "#eafaf1";
                const statusBorder = isDisrupted ? "#e8b4b1" : "#a3d9b1";
                const statusIcon = isDisrupted ? "🔴" : "🟢";
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
            // ── No LTA DataMall key configured: show a clear scope-bounded notice ──
            // Live MRT disruption posts (when any) are surfaced in the Gov Updates tab's
            // official broadcasts feed, which scrapes the LTA/SMRT Telegram channels.
            mrtEventsContent.innerHTML = banner + `
                <div style="display:flex; align-items:center; gap:8px; color: var(--text-muted); background: var(--bg-muted); border: 1px solid var(--border); padding:16px; border-radius:8px; font-size:13px; font-weight:500; line-height:1.5;">
                    <i class="fa-solid fa-circle-info" style="color:var(--primary); font-size:18px;"></i>
                    Live MRT/LRT status requires the <strong>LTA DataMall</strong> API key. Any active train disruptions are posted to the official LTA &amp; SMRT Telegram channels — see the <strong>Gov Updates</strong> tab for those broadcasts.
                </div>`;
        }
    }

    function renderGovUpdatesPane(data) {
        const banner = `<div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 4px; font-weight: 600;">
            <i class="fa-solid fa-clock-rotate-left"></i> Last synced: ${getRetrievalTimestamp()}
        </div>`;

        let govHtml = "";
        (data.gov_events || []).forEach(evt => {
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

        renderHdbResalePane(data.resale, data.resale_history);
    }

    function renderHdbResalePane(resale, history) {
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
            ${history && history.months && history.months.length > 1 ? `
            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin: 16px 0 8px;">📈 Islandwide Median Trend (${escapeHTML(history.months[0])} → ${escapeHTML(history.months[history.months.length - 1])})</div>
            <div id="hdb-resale-trend-chart" style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 10px 10px 4px;"></div>
            <div style="font-size: 11.5px; color: var(--text-muted); margin-top: 6px;">💡 Every month's islandwide median since ${escapeHTML(history.months[0])} — hover for the exact median.</div>
            ` : ''}
            <div style="font-size: 10px; color: var(--text-muted); margin-top: 10px;">💡 Source: ${escapeHTML(resale.source)}</div>
        `;

        if (history && history.months && history.months.length > 1) {
            renderLineChart(document.getElementById("hdb-resale-trend-chart"), {
                xLabels: history.months,
                series: [{ name: "Median", color: CHART_SERIES[0], values: history.medians }],
                xTickEvery: 12,
                endLabels: false,
            });
        }
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

        // The card is split into four small views behind a tab bar — one focused section
        // at a time instead of every chart, list and table stacked in a single scroll.
        const viewTabs = `
            <div style="display:flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;">
                <button class="sector-tab-btn occ-view-btn active-sector" data-occ-view="overview">💡 Overview</button>
                <button class="sector-tab-btn occ-view-btn" data-occ-view="charts">📊 Charts</button>
                <button class="sector-tab-btn occ-view-btn" data-occ-view="movers">🚀 Movers &amp; New Titles</button>
                <button class="sector-tab-btn occ-view-btn" data-occ-view="lookup">🔎 Wage Lookup</button>
            </div>`;

        container.innerHTML = banner + viewTabs + `
            <div class="occ-view" data-occ-pane="overview">
                ${tiles}
                ${insights}
                <div style="display:flex; justify-content:flex-end;">
                    <button id="occ-wage-chat-btn" data-prompt="Based on Singapore's latest MOM Occupational Wage Survey, which jobs had the best salary increment rates this year, what new AI-era job titles were created and what do they pay, and should someone in a declining occupation consider a sector change?" style="background:var(--primary); color:#ffffff; font-weight:700; border:none; padding:8px 14px; border-radius:6px; font-size:12px; cursor:pointer; transition:all 0.2s ease;">
                        <i class="fa-solid fa-robot"></i> Ask Co-Pilot for Career Insights
                    </button>
                </div>
            </div>

            <div class="occ-view hidden" data-occ-pane="charts">
                <div style="display:flex; gap: 16px; flex-wrap: wrap;">
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
            </div>

            <div class="occ-view hidden" data-occ-pane="movers">
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
                <div style="display:flex; gap: 16px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 280px;">
                        <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">🤖 Top 5 Highest-Paying Tech &amp; Digital Roles</div>
                        <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px;">${techRows}</div>
                    </div>
                    <div style="flex: 1; min-width: 280px;">
                        <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">🆕 Notable New Job Titles (🤖 = tech/AI-era)</div>
                        <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 12px 12px 4px;">
                            ${newChips || '<p style="color: var(--text-subtle); margin:0 0 8px;">No newly created titles this edition.</p>'}
                            <div style="font-size: 10px; color: var(--text-muted); margin: 4px 0 8px;">${moreNewCount > 0 ? `+${moreNewCount} more new titles — find them in the Wage Lookup tab. ` : ''}Renamed titles are already matched to their old rows and excluded.</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="occ-view hidden" data-occ-pane="lookup">
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
            </div>
        `;

        container.querySelectorAll(".occ-view-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                container.querySelectorAll(".occ-view-btn").forEach(b => b.classList.remove("active-sector"));
                btn.classList.add("active-sector");
                const view = btn.getAttribute("data-occ-view");
                container.querySelectorAll(".occ-view").forEach(p =>
                    p.classList.toggle("hidden", p.getAttribute("data-occ-pane") !== view));
                // Charts are first laid out inside a hidden pane (clientWidth 0 → fallback
                // width); re-render on reveal so they size to the real pane width.
                if (view === "charts") renderOccWageCharts(data);
            });
        });

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

            <div style="display:flex; gap:10px; margin-bottom: 12px;">
                <div style="background: var(--bg-muted); border: 1px solid var(--border); padding: 10px; border-radius: 6px; max-width: 260px;">
                    <span style="font-size: 10px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 4px; text-transform: uppercase;">📈 YoY Growth Index</span>
                    <strong style="font-size: 14px; color: ${growthColor};">${growthRate}</strong>
                </div>
                ${details.pressure && details.pressure !== "N/A" ? `
                <div style="background: var(--bg-muted); border: 1px solid var(--border); padding: 10px; border-radius: 6px; max-width: 260px;">
                    <span style="font-size: 10px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 4px; text-transform: uppercase;">⚖️ Hiring Pressure</span>
                    <strong style="font-size: 14px; color: var(--text-main);">${escapeHTML(details.pressure.split(" — ")[0])}</strong>
                </div>` : ""}
            </div>

            <div style="border-top: 1px solid var(--border); padding-top: 12px; margin-top: 12px; font-size:12px; color: var(--text-muted); line-height:1.5;">
                <strong>📈 Industry Outlook:</strong> ${escapeHTML(details.trend)}
                ${details.cagr_trend && details.cagr_trend !== "N/A" ? `<br><strong>🧭 Multi-Year Trend:</strong> ${escapeHTML(details.cagr_trend)}` : ""}
                ${details.pressure && details.pressure !== "N/A" ? `<br><strong>⚖️ Hiring Pressure:</strong> ${escapeHTML(details.pressure)}` : ""}
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

    // ==== Plain-English glossary =================================================
    // Forum complaint: gov dashboards are "peppered with acronyms" that force users to
    // open a separate Google tab to decode their own statements. Any known term rendered
    // inside SG Hub gets a dashed underline with a one-sentence explanation on hover/tap.
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
        "accrued interest": "The CPF interest you must refund (on top of the principal) to your own CPF account when you sell a property bought with CPF savings.",
    };
    const GLOSS_RE = new RegExp(
        "(?<![\\w-])("
        + Object.keys(SG_GLOSSARY).sort((a, b) => b.length - a.length)
            .map(t => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")
        + ")(?![\\w-])"
    );

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

    const hubPaneEl = document.getElementById("hub-pane");
    if (hubPaneEl) {
        let glossTimer = null;
        new MutationObserver(() => {
            if (glossAnnotating) return;
            clearTimeout(glossTimer);
            glossTimer = setTimeout(() => annotateGlossary(hubPaneEl), 250);
        }).observe(hubPaneEl, { childList: true, subtree: true });
        annotateGlossary(hubPaneEl);

        const glossTipHtml = g =>
            `<div style="font-weight:700; margin-bottom:2px;">${escapeHTML(g.dataset.term)}</div>`
            + `<div>${escapeHTML(SG_GLOSSARY[g.dataset.term] || "")}</div>`;
        hubPaneEl.addEventListener("mouseover", e => {
            const g = e.target.closest(".gloss");
            if (g) showChartTooltip(glossTipHtml(g), e.clientX, e.clientY);
        });
        hubPaneEl.addEventListener("mouseout", e => {
            if (e.target.closest(".gloss")) hideChartTooltip();
        });
        // Mobile: tap shows the explanation (no hover available); tapping elsewhere dismisses it
        hubPaneEl.addEventListener("click", e => {
            const g = e.target.closest(".gloss");
            if (g) showChartTooltip(glossTipHtml(g), e.clientX, e.clientY);
            else hideChartTooltip();
        });
    }
    // ==== end glossary ===========================================================
}

// Initialize SG Hub features on load
document.addEventListener("DOMContentLoaded", () => {
    initSgHub();
});
