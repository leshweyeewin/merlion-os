// whatsapp.js — Client logic for the WhatsApp Web Simulator.
// Interacts with backend WhatsApp endpoints and periodically polls for new messages
// to reflect pushed alerts in real-time.

(function () {
    "use strict";

    const API_PATH = "/api/whatsapp";
    const CID_KEY = "merlion_client_id";
    const PHONE_KEY = "merlion_whatsapp_phone";

    function getClientId() {
        return localStorage.getItem(CID_KEY) || "guest-client";
    }

    function getPhone() {
        let phone = localStorage.getItem(PHONE_KEY);
        if (!phone) {
            phone = "+65 " + Math.floor(80000000 + Math.random() * 19999999);
            localStorage.setItem(PHONE_KEY, phone);
        }
        return phone;
    }

    let pollInterval = null;

    function esc(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
            ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }

    // Convert WhatsApp-style markdown (*bold*, _italic_, `code`, ~strike~) to HTML
    function formatWhatsAppMessage(text) {
        if (!text) return "";
        return esc(text)
            .replace(/\*(.*?)\*/g, "<strong>$1</strong>")
            .replace(/_(.*?)_/g, "<em>$1</em>")
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            .replace(/~(.*?)~/g, "<del>$1</del>")
            .replace(/\n/g, "<br>");
    }

    function formatTime(timestamp) {
        const d = new Date(timestamp * 1000);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    async function loadHistory() {
        const chatArea = document.getElementById("wa-chat-messages");
        if (!chatArea) return;

        try {
            const res = await fetch(`${API_PATH}/history?client_id=${encodeURIComponent(getClientId())}`);
            if (!res.ok) throw new Error("Failed to load history");
            const messages = await res.json();
            renderMessages(messages);
        } catch (err) {
            console.error("Error loading WhatsApp history:", err);
        }
    }

    function renderMessages(messages) {
        const chatArea = document.getElementById("wa-chat-messages");
        if (!chatArea) return;

        // If no messages, render a system tip
        if (messages.length === 0) {
            chatArea.innerHTML = `
                <div class="wa-system-message">
                    <span>Messages are end-to-end encrypted. No one outside of this chat can read them.</span>
                </div>
                <div class="wa-system-message">
                    <span>Send <code>/start</code> or any message to begin.</span>
                </div>
            `;
            return;
        }

        const isAtBottom = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight < 50;

        let html = `
            <div class="wa-system-message">
                <span>Today</span>
            </div>
        `;

        messages.forEach(msg => {
            const isBot = msg.sender === "bot";
            const bubbleClass = isBot ? "wa-msg-received" : "wa-msg-sent";
            const ticks = isBot ? "" : `
                <span class="wa-ticks">
                    <i class="fa-solid fa-check-double"></i>
                </span>
            `;

            html += `
                <div class="wa-message-row ${isBot ? '' : 'wa-row-sent'}">
                    <div class="wa-bubble ${bubbleClass}">
                        <div class="wa-message-text">${formatWhatsAppMessage(msg.message)}</div>
                        <div class="wa-message-meta">
                            <span class="wa-time">${formatTime(msg.created_at || Date.now() / 1000)}</span>
                            ${ticks}
                        </div>
                    </div>
                </div>
            `;
        });

        chatArea.innerHTML = html;

        if (isAtBottom || chatArea.dataset.initialScroll !== "true") {
            chatArea.scrollTop = chatArea.scrollHeight;
            chatArea.dataset.initialScroll = "true";
        }
    }

    async function sendMessage(text) {
        if (!text.trim()) return;

        const input = document.getElementById("wa-user-input");
        const sendBtn = document.getElementById("wa-send-btn");

        if (input) input.value = "";
        if (input) input.disabled = true;
        if (sendBtn) sendBtn.disabled = true;

        // Optimistically append user message to local history for instant feel
        const chatArea = document.getElementById("wa-chat-messages");
        if (chatArea) {
            const now = Date.now() / 1000;
            const userRow = document.createElement("div");
            userRow.className = "wa-message-row wa-row-sent";
            userRow.innerHTML = `
                <div class="wa-bubble wa-msg-sent">
                    <div class="wa-message-text">${formatWhatsAppMessage(text)}</div>
                    <div class="wa-message-meta">
                        <span class="wa-time">${formatTime(now)}</span>
                        <span class="wa-ticks"><i class="fa-solid fa-check"></i></span>
                    </div>
                </div>
            `;
            chatArea.appendChild(userRow);
            chatArea.scrollTop = chatArea.scrollHeight;
        }

        try {
            const res = await fetch(`${API_PATH}/message`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    client_id: getClientId(),
                    message: text,
                    phone: getPhone()
                })
            });

            if (!res.ok) throw new Error("Failed to send message");
            await loadHistory();
        } catch (err) {
            console.error("WhatsApp message send error:", err);
            // Append error bubble
            if (chatArea) {
                const errRow = document.createElement("div");
                errRow.className = "wa-system-message";
                errRow.innerHTML = `<span style="background:#fde8e8; color:#9b1c1c;"><i class="fa-solid fa-triangle-exclamation"></i> Send failed: ${esc(err.message)}</span>`;
                chatArea.appendChild(errRow);
                chatArea.scrollTop = chatArea.scrollHeight;
            }
        } finally {
            if (input) input.disabled = false;
            if (sendBtn) sendBtn.disabled = false;
            if (input) input.focus();
        }
    }

    // Bootstrap function to bind events
    function initWhatsAppSimulator() {
        const phoneLabel = document.getElementById("wa-phone-number-display");
        if (phoneLabel) phoneLabel.textContent = getPhone();

        const form = document.getElementById("wa-input-form");
        const input = document.getElementById("wa-user-input");
        if (form && input) {
            form.addEventListener("submit", (e) => {
                e.preventDefault();
                const txt = input.value;
                sendMessage(txt);
            });
        }

        // Preset command pills
        document.querySelectorAll(".wa-command-pill").forEach(pill => {
            pill.addEventListener("click", () => {
                const cmd = pill.getAttribute("data-command");
                if (cmd) {
                    if (cmd === "pair") {
                        // Switch to alerts pane to get a pairing code
                        const alertTabBtn = document.getElementById("main-tab-hub-btn");
                        if (alertTabBtn) alertTabBtn.click();
                        
                        // Switch alerts sub-tab to My Alerts
                        const myAlertsSubTab = document.querySelector('[data-tab="alerts-pane"]');
                        if (myAlertsSubTab) myAlertsSubTab.click();

                        // Try to auto-trigger the Link Telegram/WhatsApp process to show the code
                        const teleLinkBtn = document.getElementById("wf-tele");
                        if (teleLinkBtn) {
                            teleLinkBtn.click();
                        }
                        
                        alert("🔑 Please copy the 6-digit code shown under the 'Link Telegram/WhatsApp' section in the Alerts Tab, then paste it here!");
                    } else if (cmd === "scam") {
                        input.value = "/check Your DBS account is locked. Verify at http://dbs-bank-verify.sg";
                        input.focus();
                    } else if (cmd === "help") {
                        sendMessage("/help");
                    } else if (cmd === "start") {
                        sendMessage("/start");
                    }
                }
            });
        });

        // Initialize history and start polling
        loadHistory();

        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(loadHistory, 4000);
    }

    // Expose init globally or run on tab activation
    window.initWhatsAppSimulator = initWhatsAppSimulator;
    
    // Auto-init if the pane is already active
    document.addEventListener("DOMContentLoaded", () => {
        const waTabBtn = document.getElementById("main-tab-whatsapp-btn");
        if (waTabBtn) {
            waTabBtn.addEventListener("click", () => {
                // Force history reload and scroll
                setTimeout(() => {
                    const chatArea = document.getElementById("wa-chat-messages");
                    if (chatArea) chatArea.dataset.initialScroll = "false";
                    loadHistory();
                }, 100);
            });
        }
        
        // Check if current tab is active on boot
        const pane = document.getElementById("whatsapp-pane");
        if (pane && !pane.classList.contains("hidden")) {
            initWhatsAppSimulator();
        } else {
            // Wait for tab click to bootstrap fully
            if (waTabBtn) {
                const bootOnce = () => {
                    initWhatsAppSimulator();
                    waTabBtn.removeEventListener("click", bootOnce);
                };
                waTabBtn.addEventListener("click", bootOnce);
            }
        }
    });

})();
