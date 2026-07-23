// persona.js — Demo life-stage personas (no real identity data). Tailors the Co-Pilot
// and surfaces relevant agencies. Exposes getActivePersona()/applyPersona() as globals.

// ── Demo personas ────────────────────────────────────────────────────────────
// Mocked life-stage profiles for the demo — NO real SingPass/identity data. Selecting one
// tailors the Co-Pilot's guidance (sent as `persona` context to the backend) and surfaces the
// agencies most relevant to that person, so the "one portal across 81 boards" story lands with
// a concrete user in mind instead of a generic wall of cards.
const PERSONA_STORAGE_KEY = "merlionos-demo-persona";
const PERSONAS = [
    {
        key: "guest",
        emoji: "👤",
        label: "Guest",
        desc: "No personalization — browse everything.",
        quickTasks: ["Renew passport", "File income tax", "Top up CPF", "CDC vouchers", "Apply for BTO", "Road tax & COE", "Register a company", "Find courses", "Check NS status"],
        chatPrompts: [
            { label: "BTO vs Resale", query: "What's the difference between a BTO and a resale flat, and what CPF housing grants can I get?" },
            { label: "SG Journey", query: "What are the requirements for the Singapore Journey onboarding?" },
            { label: "ELD Voting", query: "How do I check my electoral voting status with ELD?" },
            { label: "Climate Vouchers", query: "What are the Climate Vouchers and how do I claim them from gov.sg?" },
            { label: "Weather/PSI", query: "Check live weather forecast and air quality PSI index" },
            { label: "Job Vacancies", query: "Analyse tech industry job vacancies, YoY trend, and next-year forecast" },
            { label: "AI Job Wages", query: "Which new AI job titles appeared in Singapore's occupational wage tables this year, and what do they pay?" }
        ]
    },
    {
        key: "new-citizen",
        emoji: "🎊",
        label: "New citizen",
        desc: "32, just naturalised, renting in Punggol, tech sector.",
        greeting: "Welcome, new citizen! I can help you through the Singapore Journey, your first tax filing, CPF setup, and finding a first home. Ask me anything.",
        agencies: ["ica", "sgjourney", "cpf", "iras", "hdb", "skillsfuture"],
        quickTasks: ["Singapore Journey", "Renew passport", "Apply for BTO", "First tax filing", "Top up CPF", "SkillsFuture courses"],
        chatPrompts: [
            { label: "SG Journey", query: "What are the key steps and requirements to complete the Singapore Journey onboarding?" },
            { label: "First BTO", query: "What HDB housing grants and eligibility rules apply to newly naturalised Singapore citizens?" },
            { label: "First Tax", query: "How do I set up GIRO or pay income tax for the first time with IRAS?" },
            { label: "Passport", query: "How do I apply for a Singapore passport and IC with ICA?" }
        ],
        hubTabs: [
            { tab: "hub-hdb-pane", reason: "Buying your first home" },
            { tab: "hub-tax-pane", reason: "Your first income-tax filing" },
            { tab: "hub-jobs-pane", reason: "Tech job market & wages" },
        ],
        context: {
            label: "a new Singapore citizen",
            age: 32,
            life_stage: "recently naturalised citizen completing the Singapore Journey onboarding",
            housing: "renting an HDB flat while planning to buy a first home",
            town: "Punggol",
            sector: "technology",
        },
    },
    {
        key: "young-family",
        emoji: "👶",
        label: "Young family",
        desc: "35, new baby, HDB owner in Sengkang, healthcare sector.",
        greeting: "Hi! I can help with Baby Bonus, MediSave for delivery, preschool registration, and family grants. What would you like to sort out first?",
        agencies: ["msf", "moe", "hdb", "cpf", "healthhub", "hpb"],
        quickTasks: ["Baby Bonus", "Childcare grants", "Primary school reg", "MediSave for delivery", "BTO upgrading", "CDC vouchers"],
        chatPrompts: [
            { label: "Baby Bonus", query: "What are the cash gifts and Child Development Account (CDA) matching benefits under the Baby Bonus scheme?" },
            { label: "Preschool Reg", query: "How do I register for ECDA preschools and claim childcare subsidies?" },
            { label: "Parent Tax Reliefs", query: "What parenthood tax reliefs and Working Mother's Child Relief (WMCR) am I eligible for?" },
            { label: "MediSave Delivery", query: "Can I use MediSave for maternity expenses and hospital delivery charges?" }
        ],
        hubTabs: [
            { tab: "hub-hdb-pane", reason: "Upgrading for a growing family" },
            { tab: "hub-tax-pane", reason: "Parenthood tax reliefs" },
            { tab: "hub-community-pane", reason: "Family deals & meetups" },
        ],
        context: {
            label: "a parent in a young family",
            age: 35,
            life_stage: "a parent of a newborn managing family schemes and childcare",
            housing: "owns an HDB flat",
            town: "Sengkang",
            sector: "healthcare",
        },
    },
    {
        key: "fresh-grad",
        emoji: "🎓",
        label: "Fresh graduate",
        desc: "24, first job hunt, living in Jurong, finance sector.",
        greeting: "Hey! I can help you find jobs and career programmes, understand your first CPF contributions, and use your SkillsFuture credit. Where do we start?",
        agencies: ["mom", "wsg", "skillsfuture", "cpf", "iras"],
        quickTasks: ["Find jobs", "SkillsFuture credits", "Career conversion", "First tax filing", "CPF OA rates", "CDC vouchers"],
        chatPrompts: [
            { label: "Job Search", query: "What WSG career coaching and MyCareersFuture job programmes are available for fresh graduates?" },
            { label: "SkillsFuture", query: "How do I claim my $500 SkillsFuture Credit for professional training courses?" },
            { label: "First CPF", query: "How are CPF Ordinary, Special, and MediSave contributions allocated for a first job?" },
            { label: "First Tax", query: "Do fresh graduates earning under $20,000 need to file income tax with IRAS?" }
        ],
        hubTabs: [
            { tab: "hub-jobs-pane", reason: "Where the jobs are hiring" },
            { tab: "hub-community-pane", reason: "Budget deals & meetups" },
            { tab: "hub-tax-pane", reason: "Your first income-tax filing" },
        ],
        context: {
            label: "a fresh graduate",
            age: 24,
            life_stage: "a fresh graduate searching for a first full-time job",
            housing: "living with parents",
            town: "Jurong West",
            sector: "finance",
        },
    },
    {
        key: "retiree",
        emoji: "🌴",
        label: "Retiree",
        desc: "64, planning CPF payouts, AMK, fully-paid flat.",
        greeting: "Welcome! I can help you understand CPF LIFE payouts, healthcare subsidies, MediShield Life, and community support schemes. What can I look up for you?",
        agencies: ["cpf", "moh", "healthhub", "hpb", "cdc"],
        quickTasks: ["CPF LIFE payouts", "HealthHub appts", "Silver housing bonus", "Pioneer subsidies", "MediShield Life", "CDC vouchers"],
        chatPrompts: [
            { label: "CPF LIFE", query: "When can I start CPF LIFE payouts and what are the Standard vs Escalating payout plans?" },
            { label: "Silver Housing", query: "How does the Silver Housing Bonus work when right-sizing to a smaller HDB flat?" },
            { label: "Healthcare Subsidies", query: "What polyclinic and MediShield Life subsidies apply to Pioneer and Merdeka Generation seniors?" },
            { label: "Active Ageing", query: "What subsidized senior activities and fitness programmes are offered by ActiveSG and PA?" }
        ],
        hubTabs: [
            { tab: "hub-tax-pane", reason: "CPF & wealth planning" },
            { tab: "hub-env-pane", reason: "Daily weather & air quality" },
            { tab: "hub-gov-transit-pane", reason: "Health & scam advisories" },
        ],
        context: {
            label: "a resident planning retirement",
            age: 64,
            life_stage: "planning retirement, CPF LIFE payouts and healthcare coverage",
            housing: "owns a fully-paid HDB flat",
            town: "Ang Mo Kio",
        },
    },
];

let _activePersonaKey = "guest";

function _getPersonaByKey(key) {
    return PERSONAS.find(p => p.key === key) || PERSONAS[0];
}

// Returns the active persona's backend context ({label, age, life_stage, ...}) or null for Guest.
// Used by the chat request builder to personalize Co-Pilot answers.
function getActivePersona() {
    const p = _getPersonaByKey(_activePersonaKey);
    return (p && p.key !== "guest" && p.context) ? p.context : null;
}

function initPersona() {
    const btns = Array.from(document.querySelectorAll(".persona-select-btn"));
    const menus = Array.from(document.querySelectorAll(".persona-menu"));
    if (!btns.length || !menus.length) return;

    try {
        const saved = localStorage.getItem(PERSONA_STORAGE_KEY);
        if (saved && _getPersonaByKey(saved).key === saved) _activePersonaKey = saved;
    } catch (e) { /* localStorage may be unavailable */ }

    const menuItemsHtml = PERSONAS.map(p => `
        <button type="button" class="persona-menu-item${p.key === _activePersonaKey ? " selected" : ""}" role="option" data-persona="${p.key}" aria-selected="${p.key === _activePersonaKey}">
            <span class="persona-emoji" aria-hidden="true">${p.emoji}</span>
            <span>
                <span class="persona-item-label">${escapeHTML(p.label)}</span>
                <span class="persona-item-desc">${escapeHTML(p.desc)}</span>
            </span>
        </button>`).join("");

    menus.forEach(menu => {
        menu.innerHTML = menuItemsHtml;
    });

    const closeAllMenus = () => {
        menus.forEach(m => m.classList.add("hidden"));
        btns.forEach(b => b.setAttribute("aria-expanded", "false"));
    };

    btns.forEach(btn => {
        const wrap = btn.closest(".persona-select-wrap") || btn.parentElement;
        const menu = wrap ? wrap.querySelector(".persona-menu") : menus[0];
        if (!menu) return;

        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const willOpen = menu.classList.contains("hidden");
            closeAllMenus();
            if (willOpen) {
                menu.classList.remove("hidden");
                btn.setAttribute("aria-expanded", "true");
            }
        });
    });

    document.addEventListener("click", (e) => {
        const isClickInside = menus.some(m => m.contains(e.target)) || btns.some(b => b.contains(e.target));
        if (!isClickInside) closeAllMenus();
    });

    menus.forEach(menu => {
        menu.querySelectorAll(".persona-menu-item").forEach(item => {
            item.addEventListener("click", () => {
                applyPersona(item.getAttribute("data-persona"));
                closeAllMenus();
            });
        });
    });

    applyPersona(_activePersonaKey, /*silent=*/true);
}

function applyPersona(key, silent) {
    _activePersonaKey = _getPersonaByKey(key).key;
    try { localStorage.setItem(PERSONA_STORAGE_KEY, _activePersonaKey); } catch (e) { /* ignore */ }

    const persona = _getPersonaByKey(_activePersonaKey);
    const btns = Array.from(document.querySelectorAll(".persona-select-btn"));
    const labels = Array.from(document.querySelectorAll(".persona-select-label"));
    const menus = Array.from(document.querySelectorAll(".persona-menu"));
    const isGuest = persona.key === "guest";

    labels.forEach(lbl => { lbl.textContent = `Try as: ${persona.label}`; });
    btns.forEach(btn => { btn.classList.toggle("persona-active", !isGuest); });

    menus.forEach(menu => {
        menu.querySelectorAll(".persona-menu-item").forEach(item => {
            const sel = item.getAttribute("data-persona") === _activePersonaKey;
            item.classList.toggle("selected", sel);
            item.setAttribute("aria-selected", sel);
        });
    });

    renderPersonaPortalBanner(persona);
    renderPersonaHubBanner(persona);
    updateChatWelcome(persona);
    renderPersonaQuickTasks(persona);
    renderPersonaChatPrompts(persona);
}

function renderPersonaPortalBanner(persona) {
    const banner = document.getElementById("persona-portal-banner");
    if (!banner) return;
    if (!persona || persona.key === "guest") {
        banner.classList.add("hidden");
        banner.innerHTML = "";
        return;
    }

    const chips = (persona.agencies || []).map(agency => {
        const card = document.querySelector(`.service-card[data-agency="${agency}"]`);
        const name = card ? (card.querySelector("h3")?.textContent || agency) : agency;
        if (!card) return "";
        return `<button type="button" class="persona-chip" data-agency-target="${escapeHTML(agency)}">
            <i class="fa-solid fa-arrow-right-long" style="font-size:10px; color:var(--primary);"></i>${escapeHTML(name)}</button>`;
    }).join("");

    banner.innerHTML = `
        <div class="ppb-top">
            <span class="ppb-title">${persona.emoji} Personalized for ${escapeHTML(persona.label)}
                <span class="ppb-demo-tag" title="Demo profile only — no real SingPass or identity data is used">Demo</span>
            </span>
            <button type="button" class="ppb-clear" id="ppb-clear-btn"><i class="fa-solid fa-xmark"></i> Clear</button>
        </div>
        <div class="ppb-sub">${escapeHTML(persona.desc)} Jump to the agencies that matter most for this life-stage:</div>
        <div class="ppb-chips">${chips || '<span style="font-size:12px;color:var(--text-muted);">No matching portals on screen.</span>'}</div>`;
    banner.classList.remove("hidden");

    const clearBtn = document.getElementById("ppb-clear-btn");
    if (clearBtn) clearBtn.addEventListener("click", () => applyPersona("guest"));
    banner.querySelectorAll(".persona-chip").forEach(chip => {
        chip.addEventListener("click", () => focusPortalCard(chip.getAttribute("data-agency-target")));
    });
}

// Personalizes the SG Hub itself (not just chat + portal cards): a banner of "recommended
// dashboards for this life-stage" whose chips jump straight to the relevant hub sub-tab. Fully
// deterministic — no live AI/network call — so it stays reliable during a live demo.
function renderPersonaHubBanner(persona) {
    const banner = document.getElementById("persona-hub-banner");
    if (!banner) return;
    if (!persona || persona.key === "guest" || !(persona.hubTabs && persona.hubTabs.length)) {
        banner.classList.add("hidden");
        banner.innerHTML = "";
        return;
    }

    const chips = persona.hubTabs.map(({ tab, reason }) => {
        const tabBtn = document.querySelector(`.hub-sub-tab-btn[data-hub-sub-tab="${tab}"]`);
        if (!tabBtn) return "";
        const name = tabBtn.textContent.trim();
        return `<button type="button" class="persona-chip" data-hub-target="${escapeHTML(tab)}" title="${escapeHTML(reason)}">
            <i class="fa-solid fa-arrow-right-long" style="font-size:10px; color:var(--primary);"></i>${escapeHTML(name)}</button>`;
    }).join("");

    banner.innerHTML = `
        <div class="ppb-top">
            <span class="ppb-title">${persona.emoji} Recommended dashboards for ${escapeHTML(persona.label)}
                <span class="ppb-demo-tag" title="Demo profile only — no real SingPass or identity data is used">Demo</span>
            </span>
            <button type="button" class="ppb-clear" id="phb-clear-btn"><i class="fa-solid fa-xmark"></i> Clear</button>
        </div>
        <div class="ppb-sub">The live data views that matter most for this life-stage:</div>
        <div class="ppb-chips">${chips || '<span style="font-size:12px;color:var(--text-muted);">No matching dashboards.</span>'}</div>`;
    banner.classList.remove("hidden");

    const clearBtn = document.getElementById("phb-clear-btn");
    if (clearBtn) clearBtn.addEventListener("click", () => applyPersona("guest"));
    banner.querySelectorAll(".persona-chip").forEach(chip => {
        chip.addEventListener("click", () => focusHubTab(chip.getAttribute("data-hub-target")));
    });
}

// Switches to the SG Hub main tab (if needed), opens the given hub sub-tab, and pulses a brief
// highlight on its tab button so the recommended dashboard is obvious.
function focusHubTab(tabId) {
    const hubBtn = document.getElementById("main-tab-hub-btn");
    if (hubBtn && !hubBtn.classList.contains("active-main-tab")) hubBtn.click();
    const tabBtn = document.querySelector(`.hub-sub-tab-btn[data-hub-sub-tab="${tabId}"]`);
    if (!tabBtn) return;
    tabBtn.click();
    tabBtn.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    tabBtn.classList.add("persona-highlight");
    setTimeout(() => tabBtn.classList.remove("persona-highlight"), 1800);
}

// Scrolls a service card into view and pulses a highlight ring — switches to the SG Portals
// main tab first if the user is currently on the SG Hub.
function focusPortalCard(agency) {
    const portalsBtn = document.getElementById("main-tab-portals-btn");
    if (portalsBtn && !portalsBtn.classList.contains("active-main-tab")) portalsBtn.click();
    const card = document.querySelector(`.service-card[data-agency="${agency}"]`);
    if (!card) return;
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.classList.add("persona-highlight");
    setTimeout(() => card.classList.remove("persona-highlight"), 1800);
}

// Swaps the Co-Pilot's initial welcome bubble for a persona-tailored greeting (only the very
// first bot message, and only before any conversation has started).
function updateChatWelcome(persona) {
    const container = document.getElementById("chat-messages");
    if (!container) return;
    const firstBot = container.querySelector(".bot-message .message-content");
    if (!firstBot || container.dataset.conversationStarted === "true") return;
    if (persona && persona.key !== "guest" && persona.greeting) {
        firstBot.innerHTML = `<p><strong>${persona.emoji} ${escapeHTML(persona.label)} mode.</strong> ${escapeHTML(persona.greeting)}</p>
            <p style="font-size:11.5px; color:var(--text-muted);"><i class="fa-solid fa-circle-info"></i> Demo profile — no real identity data is used.</p>`;
    } else {
        firstBot.innerHTML = `<p>Welcome, Citizen. I am <strong>MerlionOS</strong>, your unified Singapore government assistant.</p>
            <p>Ask me anything — e.g. <em>"What are the HDB grant limits?"</em> or <em>"How much SkillsFuture credit do I have?"</em> — and I'll look it up across all relevant agencies.</p>`;
    }
}

function renderPersonaQuickTasks(persona) {
    const chipsEl = document.getElementById("quick-task-chips");
    const input = document.getElementById("portal-search-input");
    if (!chipsEl || !input) return;

    const tasks = (persona && persona.quickTasks && persona.quickTasks.length)
        ? persona.quickTasks
        : PERSONAS[0].quickTasks;

    chipsEl.innerHTML = "";
    tasks.forEach(task => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "quick-task-chip";
        chip.textContent = task;
        chip.addEventListener("click", () => {
            const active = chip.classList.contains("active-chip");
            chipsEl.querySelectorAll(".quick-task-chip").forEach(c => c.classList.remove("active-chip"));
            input.value = active ? "" : task;
            if (!active) chip.classList.add("active-chip");
            if (typeof window.applyPortalSearch === "function") {
                window.applyPortalSearch(input.value);
            }
        });
        chipsEl.appendChild(chip);
    });
}

function renderPersonaChatPrompts(persona) {
    const container = document.querySelector(".suggestions-container");
    if (!container) return;

    const prompts = (persona && persona.chatPrompts && persona.chatPrompts.length)
        ? persona.chatPrompts
        : PERSONAS[0].chatPrompts;

    container.innerHTML = prompts.map(p => `
        <button class="suggestion-chip" data-query="${escapeHTML(p.query)}">
            ${escapeHTML(p.label)}
        </button>
    `).join("");

    container.querySelectorAll(".suggestion-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const query = chip.getAttribute("data-query");
            if (typeof window.sendCoPilotMessage === "function") {
                window.sendCoPilotMessage(query);
            }
        });
    });
}

