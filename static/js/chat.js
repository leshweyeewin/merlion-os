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

    // Maps a backend tool name (from the streamed `log` events) to a human status label.
    // Every label reflects a real step the Co-Pilot is executing right now — no fabricated
    // progress. Unknown tools fall back to a generic "Consulting live sources…".
    const TOOL_STATUS_LABELS = {
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

        appendLog("system", "agent", `User initiated query parameter matching: "${text}"`);

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
                    mime_type: activeUpload.mime_type
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
                if (response.status === 429) {
                    throw Object.assign(new Error("Rate limit reached. Please wait a minute and try again."), { isRateLimit: true });
                }
                throw new Error(`HTTP Error Status: ${response.status}`);
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
                        if (event.tool === "search_singapore_government") {
                            logType = "search"; tagLabel = "search";
                            appendLog(logType, tagLabel, `Executed directory lookup search for matched query`, {
                                arguments: event.arguments, results: event.result
                            });
                        } else if (event.tool === "scrape_government_page") {
                            logType = "scrape"; tagLabel = "scrape";
                            appendLog(logType, tagLabel, `Scraped official content matching: <code>${escapeHTML(event.arguments.url || "")}</code>`, {
                                extracted_char_count: event.result.length,
                                content_preview: event.result.substring(0, 300) + "..."
                            });
                        } else {
                            appendLog(logType, tagLabel, `Intercepted static database query: <code>${escapeHTML(event.tool || "")}</code>`, {
                                arguments: event.arguments, result: event.result
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
                        // Render citation list below the streaming content inside the same bubble
                        if (botBubbleContent) {
                            const parentBubble = botBubbleContent.closest(".bot-message");
                            if (parentBubble) {
                                // Prevent duplicate citations block if received multiple times
                                let citBlock = parentBubble.querySelector(".message-citations");
                                if (!citBlock) {
                                    citBlock = document.createElement("div");
                                    citBlock.className = "message-citations";
                                    parentBubble.appendChild(citBlock);
                                }
                                citBlock.innerHTML = `
                                    <div class="citations-header"><i class="fa-solid fa-link"></i> Grounded Web Sources</div>
                                    <div class="citations-list">
                                        ${event.citations.map((c, idx) => {
                                            let domain = c.title;
                                            try {
                                                domain = new URL(c.uri).hostname.replace("www.", "");
                                            } catch (err) {}
                                            return `
                                                <a href="${safeURL(c.uri)}" target="_blank" rel="noopener noreferrer" class="citation-pill" title="${escapeHTML(c.title)}">
                                                    <strong>[${idx + 1}]</strong> ${escapeHTML(domain)}
                                                </a>
                                            `;
                                        }).join("")}
                                    </div>
                                `;
                                scrollToBottom();
                            }
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
                        throw Object.assign(new Error(event.message || "Streaming error."), {
                            isRateLimit: event.message && event.message.includes("rate limit")
                        });
                    }
                }
            }

            // If no tokens arrived at all (edge case), remove indicator
            removeTypingIndicator();

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
                userInput.required = false;
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


