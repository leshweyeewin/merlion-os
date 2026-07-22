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
    },
    {
        key: "new-citizen",
        emoji: "🎊",
        label: "New citizen",
        desc: "32, just naturalised, renting in Punggol, tech sector.",
        greeting: "Welcome, new citizen! I can help you through the Singapore Journey, your first tax filing, CPF setup, and finding a first home. Ask me anything.",
        agencies: ["ica", "sgjourney", "cpf", "iras", "hdb", "skillsfuture"],
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
    const btn = document.getElementById("persona-select-btn");
    const menu = document.getElementById("persona-menu");
    if (!btn || !menu) return;

    try {
        const saved = localStorage.getItem(PERSONA_STORAGE_KEY);
        if (saved && _getPersonaByKey(saved).key === saved) _activePersonaKey = saved;
    } catch (e) { /* localStorage may be unavailable */ }

    menu.innerHTML = PERSONAS.map(p => `
        <button type="button" class="persona-menu-item${p.key === _activePersonaKey ? " selected" : ""}" role="option" data-persona="${p.key}" aria-selected="${p.key === _activePersonaKey}">
            <span class="persona-emoji" aria-hidden="true">${p.emoji}</span>
            <span>
                <span class="persona-item-label">${escapeHTML(p.label)}</span>
                <span class="persona-item-desc">${escapeHTML(p.desc)}</span>
            </span>
        </button>`).join("");

    const closeMenu = () => { menu.classList.add("hidden"); btn.setAttribute("aria-expanded", "false"); };
    const openMenu = () => { menu.classList.remove("hidden"); btn.setAttribute("aria-expanded", "true"); };

    btn.addEventListener("click", (e) => {
        e.stopPropagation();
        menu.classList.contains("hidden") ? openMenu() : closeMenu();
    });
    document.addEventListener("click", (e) => {
        if (!menu.contains(e.target) && e.target !== btn) closeMenu();
    });
    menu.querySelectorAll(".persona-menu-item").forEach(item => {
        item.addEventListener("click", () => {
            applyPersona(item.getAttribute("data-persona"));
            closeMenu();
        });
    });

    applyPersona(_activePersonaKey, /*silent=*/true);
}

function applyPersona(key, silent) {
    _activePersonaKey = _getPersonaByKey(key).key;
    try { localStorage.setItem(PERSONA_STORAGE_KEY, _activePersonaKey); } catch (e) { /* ignore */ }

    const persona = _getPersonaByKey(_activePersonaKey);
    const btn = document.getElementById("persona-select-btn");
    const label = document.getElementById("persona-select-label");
    const menu = document.getElementById("persona-menu");
    const isGuest = persona.key === "guest";

    if (label) label.textContent = `Try as: ${persona.label}`;
    if (btn) btn.classList.toggle("persona-active", !isGuest);
    if (menu) {
        menu.querySelectorAll(".persona-menu-item").forEach(item => {
            const sel = item.getAttribute("data-persona") === _activePersonaKey;
            item.classList.toggle("selected", sel);
            item.setAttribute("aria-selected", sel);
        });
    }

    renderPersonaPortalBanner(persona);
    updateChatWelcome(persona);
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

