// chat.js — Co-Pilot chat widget: SSE streaming, tool-trace logs, uploads, and the
// primary DOMContentLoaded bootstrap that wires the portal init functions.

document.addEventListener("DOMContentLoaded", () => {
    initPortalReordering();
    initPortalVisibility();
    initPortalSearch();
    initOnboardingBanner();
    initPortalBookmarks();
    initPersona();

    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const chatMessages = document.getElementById("chat-messages");
    const logsContainer = document.getElementById("logs-container");

    // Collapsible Chat Widget DOM elements
    const chatTrigger = document.getElementById("chat-trigger");
    const chatWidget = document.getElementById("chat-widget");
    const minimizeBtn = document.getElementById("minimize-btn");
    const resetChatBtn = document.getElementById("reset-chat-btn");
    const resetConfirmModal = document.getElementById("reset-confirm-modal");
    const cancelResetBtn = document.getElementById("cancel-reset-btn");
    const confirmResetBtn = document.getElementById("confirm-reset-btn");
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

    if (resetChatBtn && resetConfirmModal) {
        resetChatBtn.addEventListener("click", () => {
            resetConfirmModal.classList.remove("hidden");
        });
    }

    if (cancelResetBtn && resetConfirmModal) {
        cancelResetBtn.addEventListener("click", () => {
            resetConfirmModal.classList.add("hidden");
        });
    }

    if (confirmResetBtn && resetConfirmModal) {
        confirmResetBtn.addEventListener("click", () => {
            resetConfirmModal.classList.add("hidden");
            resetChat();
        });
    }

    function resetChat() {
        // 1. Clear conversation history
        conversationHistory.length = 0;

        // 2. Restore initial welcome message in chat-messages container
        chatMessages.innerHTML = `
            <div class="message bot-message">
                <div class="message-avatar"><i class="fa-solid fa-landmark"></i></div>
                <div class="message-content">
                    <p>Welcome, Citizen. I am <strong>MerlionOS</strong>, your unified Singapore government assistant.</p>
                    <p>Ask me anything — e.g. <em>"What are the HDB grant limits?"</em> or <em>"How much SkillsFuture credit do I have?"</em> — and I'll look it up across all relevant agencies.</p>
                </div>
            </div>
        `;

        // 3. Clear logs container and restore initial system log entries
        const nowTime = getTimestamp();
        logsContainer.innerHTML = `
            <div class="log-entry system-entry">
                <span class="log-time">${nowTime}</span>
                <span class="log-tag tag-system">system</span>
                <span class="log-text">MerlionOS unified routing brain active.</span>
            </div>
            <div class="log-entry system-entry">
                <span class="log-time">${nowTime}</span>
                <span class="log-tag tag-system">system</span>
                <span class="log-text">Live data retrieval active for all official *.gov.sg domains.</span>
            </div>
        `;

        // 4. Reset input field
        userInput.value = "";

        // 5. If there is an active file upload, clear it
        if (typeof clearActiveUpload === "function") {
            clearActiveUpload();
        }
    }

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

    // Mirrors the backend's AUTH_URL_KEYWORDS (tools/search.py). A Google Search Grounding
    // citation can point at a SingPass/login/auth page; the system prompt forbids the model from
    // emitting a clickable login URL, so we enforce the same rule on the citations path — such a
    // source is shown as plain, non-clickable text instead of a link (anti-phishing).
    const AUTH_URL_KEYWORDS = ["login", "signin", "sign-in", "auth", "singpass", "corppass"];
    function isAuthURL(url) {
        const u = String(url).toLowerCase();
        return AUTH_URL_KEYWORDS.some(k => u.includes(k));
    }

    // Map raw server/network error strings to friendly, user-facing messages.
    // Internal exception details (stack traces, model names, Python errors) must never
    // be shown to users — log them in the Operations Trace panel instead.
    function friendlyErrorMessage(raw) {
        const msg = String(raw || "").toLowerCase();
        if (msg.includes("429") || msg.includes("quota") || msg.includes("rate limit") || msg.includes("high demand"))
            return "MerlionOS is experiencing high demand right now. Please wait a moment and try again.";
        if (msg.includes("security filter") || msg.includes("privacy") || msg.includes("pii") || msg.includes("blocked"))
            return "Your message was flagged by the security filter. Please rephrase your question and avoid sharing personal identifiers.";
        if (msg.includes("2000") || msg.includes("maximum allowed length"))
            return "Your message is too long. Please keep queries under 2,000 characters.";
        if (msg.includes("network") || msg.includes("failed to fetch"))
            return "A network error occurred. Please check your connection and try again.";
        return "Something went wrong while processing your request. Please try again.";
    }

    // Link policy (anti-phishing): only OFFICIAL Singapore government domains stay clickable —
    // *.gov.sg plus the same short trusted-domain allowlist the backend scraper uses
    // (is_trusted_sg_domain / TRUSTED_SG_DOMAINS in tools/search.py). Every other source the
    // assistant surfaces — arbitrary grounded web results, blogs, forums — is rendered as plain,
    // non-clickable text so users are never trained to click links from a chat window. Auth/login
    // pages are NEVER clickable, even on a trusted domain.
    const TRUSTED_SG_DOMAINS = ["healthhub.sg", "wsg.sg", "cdc.gov.sg"];
    function isTrustedGovURL(url) {
        if (isAuthURL(url)) return false;
        try {
            const host = new URL(url).hostname.toLowerCase();
            if (host === "gov.sg" || host.endsWith(".gov.sg")) return true;
            return TRUSTED_SG_DOMAINS.some(t => host === t || host.endsWith("." + t));
        } catch (err) {
            return false;
        }
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

        // Links: [label](url) — clickable ONLY for official *.gov.sg sources; every other link is
        // rendered as plain, non-clickable text with its source domain in muted text so the reader
        // can see where it came from and open it themselves (anti-phishing; see isTrustedGovURL).
        // Note: HTML is already escaped, so &amp; in URLs must be decoded before passing to URL().
        html = html.replace(/\[(.*?)\]\((.*?)\)/g, (match, label, rawUrl) => {
            // Decode &amp; back to & for URL parsing (HTML was escaped before this pass)
            const url = rawUrl.replace(/&amp;/g, "&");
            if (isTrustedGovURL(url)) {
                return `<a href="${safeURL(url)}" target="_blank" rel="noopener noreferrer">${label}</a>`;
            }
            let host = "";
            try {
                host = new URL(url).hostname.replace("www.", "");
            } catch (err) { }
            const src = host ? ` <span class="inline-source-host">(${host})</span>` : "";
            return `<span class="inline-source">${label}</span>${src}`;
        });

        // Bare URL auto-linker — catches raw https://... URLs the model outputs without markdown
        // formatting (e.g. "Source: https://www.hdb.gov.sg/..."). Same domain policy as above:
        // trusted gov.sg URLs → clickable link; all others → plain muted domain label.
        // Must run AFTER the [label](url) pass so it doesn't re-process already-rendered <a> tags.
        html = html.replace(/https?:\/\/[^\s<>"')\]]+/g, (rawUrl) => {
            // Decode &amp; that the HTML-escape pass may have introduced
            const url = rawUrl.replace(/&amp;/g, "&").replace(/[.,;:!?)\]]+$/, ""); // strip trailing punctuation
            if (isTrustedGovURL(url)) {
                let label = "";
                try {
                    const parsed = new URL(url);
                    // Show hostname + first path segment if present, to give useful context
                    const path = parsed.pathname.replace(/\/$/, "").split("/").slice(0, 2).join("/");
                    label = parsed.hostname.replace("www.", "") + (path || "");
                } catch (err) {
                    label = url;
                }
                return `<a href="${safeURL(url)}" target="_blank" rel="noopener noreferrer" class="auto-link">${escapeHTML(label)} <i class="fa-solid fa-up-right-from-square" style="font-size:10px;"></i></a>`;
            }
            // Non-trusted domain: show domain in muted text, no clickable link
            let host = "";
            try { host = new URL(url).hostname.replace("www.", ""); } catch (err) { }
            return host ? `<span class="inline-source-host">${escapeHTML(host)}</span>` : rawUrl;
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

    // Maps a backend tool name (from the streamed `log` events) to a human status label.
    // Every label reflects a real step the Co-Pilot is executing right now — no fabricated
    // progress. Unknown tools fall back to a generic "Consulting live sources…".
    const TOOL_STATUS_LABELS = {
        multimodal_vision_processor: "Processing uploaded document",
        search_knowledge_base: "Searching the knowledge base",
        search_singapore_government: "Searching the gov directory",
        scrape_government_page: "Reading gov.sg pages",
        google_search_grounding: "Searching the web"
    };

    function toolStatusLabel(tool) {
        return TOOL_STATUS_LABELS[tool] || "Consulting live sources";
    }

    // Updates the status text inside the live typing indicator (if it's still showing).
    function setTypingStatus(text) {
        const el = document.querySelector("#typing-indicator .typing-status-text");
        if (el) el.textContent = text;
    }

    // Render typing status indicator. Starts as "Thinking…" and gets updated in-place by
    // setTypingStatus() as real tool `log` events arrive, then dissolves on the first token.
    function showTypingIndicator() {
        const indicator = document.createElement("div");
        indicator.className = "message bot-message typing-container";
        indicator.id = "typing-indicator";
        indicator.innerHTML = `
            <div class="message-avatar"><i class="fa-solid fa-landmark"></i></div>
            <div class="message-content">
                <div class="typing-status">
                    <span class="typing-status-text">Thinking</span>
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

    // Send query message to FastAPI backend (streaming SSE with upload support)
    async function sendMessage(text) {
        if (!text.trim() && !activeUpload) return;

        const attachmentHtml = activeUpload ? `
            <div class="message-upload-attachment" style="margin-top:8px; padding:6px 10px; background:rgba(255,255,255,0.15); border-radius:4px; font-size:12px; display:inline-flex; align-items:center; gap:6px; color:#ffffff;">
                <i class="fa-solid fa-file-invoice"></i> Attachment: <strong>${escapeHTML(activeUpload.filename)}</strong>
            </div>` : "";

        // Render user message bubble
        const userMsg = document.createElement("div");
        userMsg.className = "message user-message";
        userMsg.innerHTML = `
            <div class="message-avatar"><i class="fa-solid fa-user"></i></div>
            <div class="message-content">
                <p>${text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") || "<em>[Sent document for AI analysis]</em>"}</p>
                ${attachmentHtml}
            </div>
        `;
        chatMessages.appendChild(userMsg);
        chatMessages.dataset.conversationStarted = "true";
        scrollToBottom();

        // Clear input field and toggle typing loader
        userInput.value = "";
        userInput.disabled = true;
        showTypingIndicator();

        if (text.trim()) {
            appendLog("system", "agent", `User initiated query parameter matching: "${escapeHTML(text)}"`);
        } else if (activeUpload) {
            appendLog("system", "agent", `User uploaded document for AI analysis: "<code>${escapeHTML(activeUpload.filename)}</code>"`);
        }

        if (activeUpload) {
            appendLog("multimodal", "upload", `Attached document for analysis: <code>${escapeHTML(activeUpload.filename)}</code> (${escapeHTML(activeUpload.mime_type)})`, {
                filename: activeUpload.filename,
                mime_type: activeUpload.mime_type,
                size_approx: Math.round((activeUpload.base64.length * 3) / 4) + " bytes"
            });
        }

        // Create the bot bubble early — tokens stream into it
        let accumulated = "";
        let botBubbleContent = null;

        try {
            const reqBody = {
                message: text,
                history: conversationHistory
            };
            if (activeUpload) {
                reqBody.file = {
                    base64: activeUpload.base64,
                    mime_type: activeUpload.mime_type,
                    filename: activeUpload.filename
                };
            }
            const activePersona = getActivePersona();
            if (activePersona) reqBody.persona = activePersona;

            const response = await fetch("/api/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(reqBody)
            });

            if (!response.ok) {
                let errorMessage = `HTTP Error Status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData.detail) {
                        errorMessage = errorData.detail;
                    }
                } catch (e) {
                    // If parsing fails, use the status-based message
                }
                
                if (response.status === 429) {
                    throw Object.assign(new Error(errorMessage), { isRateLimit: true });
                }
                throw new Error(errorMessage);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // SSE lines are delimited by double newline
                const parts = buffer.split("\n\n");
                buffer = parts.pop(); // keep incomplete tail

                for (const part of parts) {
                    const line = part.trim();
                    if (!line.startsWith("data:")) continue;

                    let event;
                    try {
                        event = JSON.parse(line.slice(5).trim());
                    } catch {
                        continue;
                    }

                    if (event.type === "log") {
                        // Reflect the tool the Co-Pilot is running as a live status line in the
                        // chat bubble (in addition to the detailed Operations Terminal entry below).
                        setTypingStatus(toolStatusLabel(event.tool));

                        // Tool execution log — render to Operations Terminal
                        let logType = "system", tagLabel = "integration";
                        if (event.tool === "multimodal_vision_processor") {
                            logType = "multimodal"; tagLabel = "vision";
                            appendLog(logType, tagLabel, `Decoded Base64 document payload for Gemini 2.5 Flash analysis: <code>${escapeHTML(event.arguments.filename || "document")}</code>`, {
                                arguments: event.arguments,
                                result: event.result
                            });
                        } else if (event.tool === "search_knowledge_base") {
                            logType = "search"; tagLabel = "rag";
                            const queryText = event.arguments ? (event.arguments.query || event.arguments.user_query || JSON.stringify(event.arguments)) : "";
                            appendLog(logType, tagLabel, `Queried RAG Civic Knowledge Base (gemini-embedding-001 vector similarity matching) for: "<code>${escapeHTML(queryText)}</code>"`, {
                                arguments: event.arguments,
                                results: event.result
                            });
                        } else if (event.tool === "search_singapore_government") {
                            logType = "search"; tagLabel = "directory";
                            const queryText = event.arguments ? (event.arguments.query || JSON.stringify(event.arguments)) : "";
                            appendLog(logType, tagLabel, `Executed 82 Statutory Directory lookup search for: "<code>${escapeHTML(queryText)}</code>"`, {
                                arguments: event.arguments,
                                results: event.result
                            });
                        } else if (event.tool === "scrape_government_page") {
                            logType = "scrape"; tagLabel = "scrape";
                            appendLog(logType, tagLabel, `Scraped official content matching: <code>${escapeHTML(event.arguments.url || "")}</code>`, {
                                extracted_char_count: typeof event.result === "string" ? event.result.length : JSON.stringify(event.result).length,
                                content_preview: typeof event.result === "string" ? (event.result.substring(0, 300) + "...") : event.result
                            });
                        } else {
                            logType = "system"; tagLabel = "tool";
                            appendLog(logType, tagLabel, `Executed statutory tool query: <code>${escapeHTML(event.tool || "")}</code>`, {
                                arguments: event.arguments,
                                result: event.result
                            });
                        }

                    } else if (event.type === "token") {
                        // First token — remove typing indicator, create bot bubble
                        if (!botBubbleContent) {
                            removeTypingIndicator();
                            const botBubble = document.createElement("div");
                            botBubble.className = "message bot-message";
                            botBubble.innerHTML = `
                                <div class="message-avatar"><i class="fa-solid fa-landmark"></i></div>
                                <div class="message-content streaming-content"></div>
                            `;
                            chatMessages.appendChild(botBubble);
                            botBubbleContent = botBubble.querySelector(".streaming-content");
                        }
                        accumulated += event.text;
                        // Re-render markdown on each token so formatting appears progressively
                        botBubbleContent.innerHTML = renderMarkdown(accumulated);
                        scrollToBottom();

                    } else if (event.type === "citations") {
                        // Render citation chips inline inside the message-content, right after the text
                        if (botBubbleContent) {
                            // Prevent duplicate citations block across multiple citation events
                            let citBlock = botBubbleContent.querySelector(".message-citations");
                            if (!citBlock) {
                                citBlock = document.createElement("div");
                                citBlock.className = "message-citations";
                                botBubbleContent.appendChild(citBlock);
                            }
                            citBlock.innerHTML = `
                                <div class="citations-list">
                                    ${event.citations.map((c, idx) => {
                                let domain = c.title;
                                try {
                                    const parsed = new URL(c.uri);
                                    // Show hostname + first meaningful path segment for context
                                    const seg = parsed.pathname.replace(/\/$/, "").split("/").filter(Boolean)[0];
                                    domain = parsed.hostname.replace("www.", "") + (seg ? "/" + seg : "");
                                } catch (err) { }
                                // Link policy: official *.gov.sg sources → clickable; auth/login/non-gov → plain chip
                                if (isTrustedGovURL(c.uri)) {
                                    return `<a href="${safeURL(c.uri)}" target="_blank" rel="noopener noreferrer" class="citation-pill" title="${escapeHTML(c.title)}">[${idx + 1}] ${escapeHTML(domain)} <i class="fa-solid fa-up-right-from-square" style="font-size:9px;opacity:0.7"></i></a>`;
                                }
                                const isAuth = isAuthURL(c.uri);
                                const shield = isAuth ? ' <i class="fa-solid fa-shield-halved" aria-hidden="true"></i>' : '';
                                const tip = isAuth
                                    ? "Open this yourself in a new browser tab — never follow login links from a chat assistant"
                                    : escapeHTML(c.title);
                                return `<span class="citation-pill citation-pill-noauth" title="${tip}">[${idx + 1}] ${escapeHTML(domain)}${shield}</span>`;
                            }).join("")}
                                </div>
                            `;
                            scrollToBottom();
                        }

                    } else if (event.type === "done") {
                        // Finalise history
                        conversationHistory.push({ role: "user", content: text });
                        conversationHistory.push({ role: "model", content: accumulated });
                        if (botBubbleContent) {
                            botBubbleContent.classList.remove("streaming-content");
                        }
                        appendLog("system", "success", "Response streamed and formatted successfully.");


                    } else if (event.type === "error") {
                        removeTypingIndicator();
                        const friendly = friendlyErrorMessage(event.message);
                        // Log the raw message to the Operations Trace for debugging, but only
                        // show the friendly version in the chat bubble.
                        appendLog("error", "error", `Request failed: ${escapeHTML(event.message || "Unknown error")}`);
                        throw Object.assign(new Error(friendly), {
                            isRateLimit: event.message && (event.message.includes("rate limit") || event.message.includes("demand") || event.message.includes("429")),
                            alreadyLogged: true
                        });
                    }
                }
            }

            // If no tokens arrived at all (edge case), remove indicator
            removeTypingIndicator();

        } catch (error) {
            removeTypingIndicator();
            // Only log to Operations Trace if the error hasn't been logged already (SSE errors
            // are logged inline above so we avoid a duplicate entry).
            if (!error.alreadyLogged) {
                appendLog("error", "error", `Request failed: ${escapeHTML(error.message)}`);
            }

            const displayMsg = friendlyErrorMessage(error.message);
            const errorMsg = document.createElement("div");
            errorMsg.className = "message bot-message";
            if (error.isRateLimit) {
                errorMsg.innerHTML = `
                    <div class="message-avatar"><i class="fa-solid fa-landmark"></i></div>
                    <div class="message-content">
                        <p style="color: var(--text-warning);"><i class="fa-solid fa-clock"></i> <strong>Service Busy:</strong> ${escapeHTML(displayMsg)}</p>
                    </div>
                `;
            } else {
                errorMsg.innerHTML = `
                    <div class="message-avatar"><i class="fa-solid fa-landmark"></i></div>
                    <div class="message-content">
                        <p style="color: var(--text-error);"><i class="fa-solid fa-triangle-exclamation"></i> <strong>Unable to process request:</strong> ${escapeHTML(displayMsg)}</p>
                    </div>
                `;
            }
            chatMessages.appendChild(errorMsg);
        } finally {
            userInput.disabled = false;
            clearActiveUpload();
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


    // Preset suggestion pills are rendered and bound by persona.js (renderPersonaChatPrompts),
    // which owns them so they can be swapped per persona — expose sendMessage for it to call.
    window.sendCoPilotMessage = sendMessage;

    // Multimodal document upload bindings (Item 9)
    let activeUpload = null;
    const chatFileBtn = document.getElementById("chat-file-btn");
    const chatFileInput = document.getElementById("chat-file-input");
    const uploadPreview = document.getElementById("upload-preview");
    const previewFilename = document.getElementById("preview-filename");
    const clearUploadBtn = document.getElementById("clear-upload-btn");

    if (chatFileBtn && chatFileInput) {
        chatFileBtn.addEventListener("click", () => {
            chatFileInput.click();
        });

        chatFileInput.addEventListener("change", () => {
            const file = chatFileInput.files[0];
            if (!file) return;

            // 1. Define strict validation rules
            const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
            const maxSizeBytes = 5 * 1024 * 1024; // 5MB limit

            // 2. Validate File Type (Blocks PDFs and raw docs)
            if (!allowedTypes.includes(file.type)) {
                alert("🚨 Document formats (like PDFs) are not allowed. Please upload an image (.jpg, .png, .webp) instead.");
                chatFileInput.value = ''; // Reset the input field
                return; // Terminate execution immediately
            }

            // 3. Validate File Size
            if (file.size > maxSizeBytes) {
                alert("⚠️ File is too large. Please upload an image smaller than 5MB to prevent processing large document sets.");
                chatFileInput.value = ''; // Reset the input field
                return; // Terminate execution immediately
            }

            // 4. Proceed with processing if validations pass
            const reader = new FileReader();
            reader.onload = () => {
                const parts = reader.result.split(",");
                const base64 = parts[1];
                const mime_type = file.type;

                activeUpload = {
                    base64: base64,
                    mime_type: mime_type,
                    filename: file.name
                };

                if (previewFilename && uploadPreview) {
                    previewFilename.textContent = file.name;
                    uploadPreview.classList.remove("hidden");
                }
                if (userInput) userInput.required = false;
            };
            reader.readAsDataURL(file);
        });
    }

    function clearActiveUpload() {
        activeUpload = null;
        if (chatFileInput) chatFileInput.value = "";
        if (uploadPreview) uploadPreview.classList.add("hidden");
        userInput.required = true;
    }

    if (clearUploadBtn) {
        clearUploadBtn.addEventListener("click", () => {
            clearActiveUpload();
        });
    }
});


