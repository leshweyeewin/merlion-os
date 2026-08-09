// persona.js — Demo life-stage personas (no real identity data). Tailors the Co-Pilot
// and surfaces relevant agencies. Exposes getActivePersona()/applyPersona() as globals.

// ── Demo personas ────────────────────────────────────────────────────────────
// Mocked life-stage profiles for the demo — NO real SingPass/identity data. Selecting one
// tailors the Co-Pilot's guidance (sent as `persona` context to the backend) and surfaces the
// agencies most relevant to that person, so the "one portal across 82 boards" story lands with
// a concrete user in mind instead of a generic wall of cards.
const PERSONA_STORAGE_KEY = "merlionos-demo-persona";
const PERSONA_LOCALIZATION = {
    en: {
        labels: { "guest": "Guest", "new-citizen": "New citizen", "young-family": "Young family", "fresh-grad": "Fresh graduate", "retiree": "Retiree" },
        tryAs: "Try as",
        personalizedFor: "Personalized for",
        jumpToAgencies: "Jump to the agencies that matter most for this life-stage:",
        clear: "Clear",
        demoTag: "Demo",
        quickTasks: {
            "Renew passport": "Renew passport", "File income tax": "File income tax", "Top up CPF": "Top up CPF", "CDC vouchers": "CDC vouchers", "Apply for BTO": "Apply for BTO", "Road tax & COE": "Road tax & COE", "Register a company": "Register a company", "Find courses": "Find courses", "Check NS status": "Check NS status", "Singapore Journey": "Singapore Journey", "First tax filing": "First tax filing", "SkillsFuture courses": "SkillsFuture courses", "Baby Bonus": "Baby Bonus", "Childcare grants": "Childcare grants", "Primary school reg": "Primary school reg", "MediSave for delivery": "MediSave for delivery", "BTO upgrading": "BTO upgrading", "Job Search": "Job Search", "Career conversion": "Career conversion", "CPF LIFE": "CPF LIFE", "MediShield Life": "MediShield Life", "Eldercare grants": "Eldercare grants", "Senior Bonus": "Senior Bonus", "ActiveSG credits": "ActiveSG credits"
        },
        descs: {
            "guest": "No personalization — browse everything.",
            "new-citizen": "32, just naturalised, renting in Punggol, tech sector.",
            "young-family": "35, new baby, HDB owner in Sengkang, healthcare sector.",
            "fresh-grad": "25, job-seeking, living in Jurong West, public sector candidate.",
            "retiree": "67, retired, HDB owner in Toa Payoh, focus on CPF LIFE & MediShield."
        }
    },
    zh: {
        labels: { "guest": "访客", "new-citizen": "新公民", "young-family": "年轻家庭", "fresh-grad": "应届毕业生", "retiree": "退休人士" },
        tryAs: "切换身份",
        personalizedFor: "为您定制",
        jumpToAgencies: "快速跳转至适合该阶段的政府机构门户：",
        clear: "清除",
        demoTag: "演示",
        quickTasks: {
            "Renew passport": "更新护照", "File income tax": "申报所得税", "Top up CPF": "充值 CPF", "CDC vouchers": "领取 CDC 消费券", "Apply for BTO": "申请 BTO 组屋", "Road tax & COE": "路税与 COE", "Register a company": "注册公司", "Find courses": "查找技能课程", "Check NS status": "查询国民服役", "Singapore Journey": "新加坡公民之旅", "First tax filing": "首次申报所得税", "SkillsFuture courses": "SkillsFuture 课程", "Baby Bonus": "育儿津贴与花红", "Childcare grants": "托儿补助金", "Primary school reg": "小一入学报名", "MediSave for delivery": "生育 MediSave 扣除", "BTO upgrading": "BTO 提升住房", "Job Search": "求职与职位搜索", "Career conversion": "职业转型计划", "CPF LIFE": "CPF LIFE 终身养老金", "MediShield Life": "终身健保", "Eldercare grants": "乐龄护理津贴", "Senior Bonus": "乐龄特别花红", "ActiveSG credits": "乐龄运动积分"
        },
        descs: {
            "guest": "无个性化配置 — 浏览所有功能",
            "new-citizen": "32岁，刚入籍公民，租住榜鹅，科技行业。",
            "young-family": "35岁，新手父母，盛港组屋业主，医疗保健行业。",
            "fresh-grad": "25岁，寻找首份工作，居住在裕廊西，公共部门准员工。",
            "retiree": "67岁，退休人士，大巴窑组屋业主，关注养老金与医疗。"
        }
    },
    ms: {
        labels: { "guest": "Tetamu", "new-citizen": "Warganegara baru", "young-family": "Keluarga muda", "fresh-grad": "Graduan baru", "retiree": "Pesara" },
        tryAs: "Cuba sebagai",
        personalizedFor: "Disesuaikan untuk",
        jumpToAgencies: "Lompat ke agensi penting untuk fasa kehidupan ini:",
        clear: "Kosongkan",
        demoTag: "Demo",
        quickTasks: {
            "Renew passport": "Perbaharui pasport", "File income tax": "Failkan cukai", "Top up CPF": "Tambah nilai CPF", "CDC vouchers": "Baucar CDC", "Apply for BTO": "Memohon BTO", "Road tax & COE": "Cukai jalan & COE", "Register a company": "Daftar syarikat", "Find courses": "Cari kursus", "Check NS status": "Semak status NS", "Singapore Journey": "Singapura Journey", "First tax filing": "Failkan cukai pertama", "SkillsFuture courses": "Kursus SkillsFuture", "Baby Bonus": "Bonus Bayi", "Childcare grants": "Geran penjagaan anak", "Primary school reg": "Pendaftaran sekolah rendah", "MediSave for delivery": "MediSave untuk bersalin", "BTO upgrading": "Naik taraf BTO", "Job Search": "Cari Kerja", "Career conversion": "Penukaran Kerjaya", "CPF LIFE": "CPF LIFE", "MediShield Life": "MediShield Life", "Eldercare grants": "Geran penjagaan warga emas", "Senior Bonus": "Bonus Warga Emas", "ActiveSG credits": "Kredit ActiveSG"
        },
        descs: {
            "guest": "Tiada pemperibadian — semak semua.",
            "new-citizen": "32, baru dinaturalisasikan, menyewa di Punggol, sektor teknologi.",
            "young-family": "35, bayi baru, pemilik HDB di Sengkang, sektor kesihatan.",
            "fresh-grad": "25, mencari pekerjaan pertama, tinggal di Jurong West.",
            "retiree": "67, bersara, pemilik HDB di Toa Payoh."
        }
    },
    ta: {
        labels: { "guest": "விருந்தினர்", "new-citizen": "புதிய குடிமகன்", "young-family": "இளம் குடும்பம்", "fresh-grad": "புதிய பட்டதாரி", "retiree": "ஓய்வுபெற்றவர்" },
        tryAs: "முயற்சிக்க",
        personalizedFor: "தனிப்பயனாக்கப்பட்டது",
        jumpToAgencies: "முக்கிய ஏஜென்சிகளுக்கு செல்லவும்:",
        clear: "அழி",
        demoTag: "டெமோ",
        quickTasks: {
            "Renew passport": "பாஸ்போர்ட் புதுப்பித்தல்", "File income tax": "வருமான வரி தாக்கல்", "Top up CPF": "CPF டாப் அப்", "CDC vouchers": "CDC வவுச்சர்கள்", "Apply for BTO": "BTO விண்ணப்பிக்க", "Road tax & COE": "சாலை வரி & COE", "Register a company": "நிறுவனம் பதிவு செய்ய", "Find courses": "பயிற்சிகள் தேட", "Check NS status": "NS நிலையை சரிபார்க்க", "Singapore Journey": "சிங்கப்பூர் பயணம்", "First tax filing": "முதல் வரி தாக்கல்", "SkillsFuture courses": "SkillsFuture பயிற்சிகள்", "Baby Bonus": "குழந்தை போனஸ்", "Childcare grants": "குழந்தை பராமரிப்பு மானியம்", "Primary school reg": "தொடக்கப்பள்ளி பதிவு", "MediSave for delivery": "பிரசவத்திற்கு MediSave", "BTO upgrading": "BTO மேம்பாடு", "Job Search": "வேலை தேடுதல்", "Career conversion": "தொழில் மாற்றம்", "CPF LIFE": "CPF LIFE", "MediShield Life": "MediShield Life", "Eldercare grants": "முதியோர் பராமரிப்பு மானியம்", "Senior Bonus": "மூத்த குடிமகன் போனஸ்", "ActiveSG credits": "ActiveSG கிரெடிட்கள்"
        },
        descs: {
            "guest": "தனிப்பயனாக்கம் இல்லை — அனைத்தையும் பார்க்கவும்.",
            "new-citizen": "32, புதிதாக குடியுரிமை பெற்றவர், பொங்கோலில் வாடகை, தொழில்நுட்பத் துறை.",
            "young-family": "35, புதிய குழந்தை, செங்காங்கில் HDB உரிமையாளர்.",
            "fresh-grad": "25, முதல் வேலை தேடுகிறார், ஜூரோங் வெஸ்ட்.",
            "retiree": "67, ஓய்வு பெற்றவர், தோவா பயோவில் HDB உரிமையாளர்."
        }
    }
};

function _getPersonaLoc() {
    const lang = window.currentLanguage || localStorage.getItem("merlion_language") || "en";
    return PERSONA_LOCALIZATION[lang] || PERSONA_LOCALIZATION.en;
}

function _getLocalizedPersonaLabel(pKey) {
    const loc = _getPersonaLoc();
    return (loc.labels && loc.labels[pKey]) || (_getPersonaByKey(pKey)?.label || pKey);
}

function _getLocalizedPersonaDesc(pKey) {
    const loc = _getPersonaLoc();
    return (loc.descs && loc.descs[pKey]) || (_getPersonaByKey(pKey)?.desc || "");
}

function _getLocalizedQuickTask(taskName) {
    const loc = _getPersonaLoc();
    return (loc.quickTasks && loc.quickTasks[taskName]) || taskName;
}

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
            { label: "BTO vs Resale", query: "As a newly naturalised citizen renting in Punggol, what's the difference between a BTO and a resale flat, and which CPF housing grants can I get?" },
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
        desc: "25, job-seeking, living in Jurong West, public sector candidate.",
        greeting: "Hello! I can guide you on MySkillsFuture credits, job vacancy trends, salary benchmarks, and CPF contribution rules. What's on your mind?",
        agencies: ["wsg", "skillsfuture", "mom", "cpf", "nlb", "mccy"],
        quickTasks: ["SkillsFuture courses", "Job Search", "Top up CPF", "Career conversion", "CDC vouchers"],
        chatPrompts: [
            { label: "Wage Explorer", query: "What are the starting salaries and YoY wage growth for entry-level tech and finance roles?" },
            { label: "SkillsFuture", query: "How do I claim my $500 SkillsFuture Credit for career courses?" },
            { label: "CPF Rates", query: "What is the employee and employer CPF contribution rate for a 25-year-old?" }
        ],
        hubTabs: [
            { tab: "hub-jobs-pane", reason: "Job market analytics & wage benchmarks" },
            { tab: "hub-community-pane", reason: "Lifestyle deals & learning events" },
        ],
        context: {
            label: "a fresh graduate entering the workforce",
            age: 25,
            life_stage: "recent university graduate looking for first job and skill upgrading",
            housing: "living with parents",
            town: "Jurong West",
            sector: "job seeker",
        },
    },
    {
        key: "retiree",
        emoji: "🍵",
        label: "Retiree",
        desc: "67, retired, HDB owner in Toa Payoh, focus on CPF LIFE & MediShield.",
        greeting: "Good day! I can assist with CPF LIFE payout projections, MediSave for clinic visits, Silver Support, and active aging programmes.",
        agencies: ["cpf", "healthhub", "hpb", "pa", "msf", "nlb"],
        quickTasks: ["CPF LIFE", "MediShield Life", "Eldercare grants", "Senior Bonus", "ActiveSG credits", "CDC vouchers"],
        chatPrompts: [
            { label: "CPF LIFE Payouts", query: "How are monthly payouts calculated under CPF LIFE Standard vs Basic Plan?" },
            { label: "Senior Subsidies", query: "What healthcare subsidies, Pioneer/Merdeka Generation benefits am I eligible for at polyclinics?" },
            { label: "Silver Support", query: "What are the eligibility criteria for the Silver Support Scheme quarterly cash payouts?" }
        ],
        hubTabs: [
            { tab: "hub-community-pane", reason: "Community & senior wellness activities" },
            { tab: "hub-hdb-pane", reason: "Lease Buyback & Silver Housing Bonus" },
        ],
        context: {
            label: "a retired senior citizen",
            age: 67,
            life_stage: "retiree managing retirement payouts and healthcare benefits",
            housing: "owns a fully paid-up HDB flat",
            town: "Toa Payoh",
            sector: "retired",
        },
    },
];

let _activePersonaKey = "guest";

function _getPersonaByKey(key) {
    return PERSONAS.find(p => p.key === key) || PERSONAS[0];
}

function getActivePersonaKey() {
    return _activePersonaKey;
}
window.getActivePersonaKey = getActivePersonaKey;

// Returns the active persona's backend context ({label, age, life_stage, ...}) or null for Guest.
// Used by the chat request builder to personalize Co-Pilot answers.
function getActivePersona() {
    const p = _getPersonaByKey(_activePersonaKey);
    return (p && p.key !== "guest" && p.context) ? p.context : null;
}

function renderPersonaMenuItems() {
    const menus = Array.from(document.querySelectorAll(".persona-menu"));
    if (!menus.length) return;
    const menuItemsHtml = PERSONAS.map(p => {
        const label = _getLocalizedPersonaLabel(p.key);
        const desc = _getLocalizedPersonaDesc(p.key);
        return `
        <button type="button" class="persona-menu-item${p.key === _activePersonaKey ? " selected" : ""}" role="option" data-persona="${p.key}" aria-selected="${p.key === _activePersonaKey}">
            <span class="persona-emoji" aria-hidden="true">${p.emoji}</span>
            <span>
                <span class="persona-item-label">${escapeHTML(label)}</span>
                <span class="persona-item-desc">${escapeHTML(desc)}</span>
            </span>
        </button>`;
    }).join("");

    menus.forEach(menu => {
        menu.innerHTML = menuItemsHtml;
        menu.querySelectorAll(".persona-menu-item").forEach(item => {
            item.addEventListener("click", () => {
                applyPersona(item.getAttribute("data-persona"));
                menu.classList.add("hidden");
            });
        });
    });
}

function initPersona() {
    const btns = Array.from(document.querySelectorAll(".persona-select-btn"));
    const menus = Array.from(document.querySelectorAll(".persona-menu"));
    if (!btns.length || !menus.length) return;

    try {
        const saved = localStorage.getItem(PERSONA_STORAGE_KEY);
        if (saved && _getPersonaByKey(saved).key === saved) _activePersonaKey = saved;
    } catch (e) { /* localStorage may be unavailable */ }

    renderPersonaMenuItems();

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

    applyPersona(_activePersonaKey, /*silent=*/true);
}

function applyPersona(key, silent) {
    _activePersonaKey = _getPersonaByKey(key).key;
    try { localStorage.setItem(PERSONA_STORAGE_KEY, _activePersonaKey); } catch (e) { /* ignore */ }

    const persona = _getPersonaByKey(_activePersonaKey);
    const loc = _getPersonaLoc();
    const localizedLabel = _getLocalizedPersonaLabel(persona.key);
    const btns = Array.from(document.querySelectorAll(".persona-select-btn"));
    const labels = Array.from(document.querySelectorAll(".persona-select-label"));
    const menus = Array.from(document.querySelectorAll(".persona-menu"));
    const isGuest = persona.key === "guest";

    renderPersonaMenuItems();

    labels.forEach(lbl => { lbl.textContent = `${loc.tryAs}: ${localizedLabel}`; });
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

    const loc = _getPersonaLoc();
    const localizedLabel = _getLocalizedPersonaLabel(persona.key);
    const localizedDesc = _getLocalizedPersonaDesc(persona.key);

    const chips = (persona.agencies || []).map(agency => {
        const card = document.querySelector(`.service-card[data-agency="${agency}"]`);
        const name = card ? (card.querySelector("h3")?.textContent || agency) : agency;
        if (!card) return "";
        return `<button type="button" class="persona-chip" data-agency-target="${escapeHTML(agency)}">
            <i class="fa-solid fa-arrow-right-long" style="font-size:10px; color:var(--primary);"></i>${escapeHTML(name)}</button>`;
    }).join("");

    banner.innerHTML = `
        <div class="ppb-top">
            <span class="ppb-title">${persona.emoji} ${escapeHTML(loc.personalizedFor)} ${escapeHTML(localizedLabel)}
                <span class="ppb-demo-tag" title="Demo profile only — no real SingPass or identity data is used">${escapeHTML(loc.demoTag)}</span>
            </span>
            <button type="button" class="ppb-clear" id="ppb-clear-btn"><i class="fa-solid fa-xmark"></i> ${escapeHTML(loc.clear)}</button>
        </div>
        <div class="ppb-sub">${escapeHTML(localizedDesc)} ${escapeHTML(loc.jumpToAgencies)}</div>
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
        const localizedTask = _getLocalizedQuickTask(task);
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "quick-task-chip";
        chip.textContent = localizedTask;
        chip.setAttribute("data-task-key", task);
        chip.addEventListener("click", () => {
            const active = chip.classList.contains("active-chip");
            chipsEl.querySelectorAll(".quick-task-chip").forEach(c => c.classList.remove("active-chip"));
            input.value = active ? "" : localizedTask;
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

