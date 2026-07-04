document.addEventListener("DOMContentLoaded", () => {
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

        // Links: [label](url)
        html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

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
            <div class="message-avatar">🦁</div>
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
                body: JSON.stringify({ message: text })
            });

            if (!response.ok) {
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
                        appendLog(logType, tagLabel, `Executed directory lookup search for matched query`, {
                            arguments: log.arguments,
                            results: log.result
                        });
                    } else if (log.tool === "scrape_government_page") {
                        logType = "scrape";
                        tagLabel = "scrape";
                        appendLog(logType, tagLabel, `Scraped official content matching: <code>${log.arguments.url}</code>`, {
                            extracted_char_count: log.result.length,
                            content_preview: log.result.substring(0, 300) + "..."
                        });
                    } else {
                        appendLog(logType, tagLabel, `Intercepted static database query: <code>${log.tool}</code>`, {
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
                <div class="message-avatar">🦁</div>
                <div class="message-content">
                    ${renderMarkdown(data.response)}
                </div>
            `;
            chatMessages.appendChild(botMsg);
            
            appendLog("system", "success", "Response compiled and formatted successfully.");

        } catch (error) {
            removeTypingIndicator();
            appendLog("error", "error", `API handshake failed: ${error.message}`);

            const errorMsg = document.createElement("div");
            errorMsg.className = "message bot-message";
            errorMsg.innerHTML = `
                <div class="message-avatar">🦁</div>
                <div class="message-content">
                    <p style="color: var(--text-error);"><i class="fa-solid fa-triangle-exclamation"></i> <strong>Execution Error:</strong> Failed to fetch guidance coordinates. Please check your network or server logs.</p>
                </div>
            `;
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
