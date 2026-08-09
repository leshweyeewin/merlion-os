// translations.js — Manage multilingual localization (EN, ZH, MS, TA)
// and elderly accessibility/large-text mode settings on the frontend.

const TRANSLATIONS = {
    en: {
        "app-title": "Singapore Government Digital Services Portal",
        "app-subtitle": "Access statutory directories and live data.gov.sg metrics in a unified dashboard.",
        "tab-portals": "SG Portals",
        "tab-hub": "SG Hub",
        "tab-whatsapp": "WhatsApp Simulator",
        "chat-disclaimer": "AI can make mistakes and this is not financial, tax or legal advice. Please double-check responses against official government portals before acting.",
        "privacy-note": "Privacy Note: Do not upload ID cards, passports, tax returns, or sensitive personal statements. Uploaded images are processed by AI for analysis only.",
        "suggest-bto": "BTO vs Resale",
        "suggest-journey": "SG Journey",
        "suggest-voting": "ELD Voting",
        "suggest-climate": "Climate Vouchers",
        "suggest-weather": "Weather/PSI",
        "suggest-jobs": "Job Vacancies",
        "suggest-wages": "AI Job Wages",
        "document-copilot-title": "Document Copilot",
        "document-copilot-desc": "Generate and upload simulated mock documents to test the multimodal vision and policy advice engines.",
        "sim-noa": "Simulate IRAS Notice of Assessment (NOA)",
        "sim-cpf": "Simulate CPF Statement",
        "sim-payslip": "Simulate monthly payslip",
        "elderly-mode-label": "Elderly Mode",
        "lang-label": "Language"
    },
    zh: {
        "app-title": "新加坡政府数字化服务门户",
        "app-subtitle": "在统一的控制面板中访问法定名录和实时 data.gov.sg 指标。",
        "tab-portals": "新加坡门户",
        "tab-hub": "新加坡中心",
        "tab-whatsapp": "WhatsApp 模拟器",
        "chat-disclaimer": "AI 可能会犯错，此内容不构成财务、税务或法律建议。在采取行动之前，请先登录官方政府门户网站复核。",
        "privacy-note": "隐私提示：请勿上传身份证、护照、报税单或敏感个人账单。上传的图片仅供 AI 分析处理。",
        "suggest-bto": "组屋 vs 转售屋",
        "suggest-journey": "新加坡之旅",
        "suggest-voting": "选民登记查询",
        "suggest-climate": "绿色环保券",
        "suggest-weather": "天气与 PSI 指数",
        "suggest-jobs": "行业职位分析",
        "suggest-wages": "AI 职位薪资",
        "document-copilot-title": "文档副驾驶",
        "document-copilot-desc": "生成并上传模拟文件，测试多模态视觉与政策建议引擎。",
        "sim-noa": "模拟 IRAS 税收评估通知 (NOA)",
        "sim-cpf": "模拟 CPF 缴存单",
        "sim-payslip": "模拟每月工资单",
        "elderly-mode-label": "老年模式",
        "lang-label": "语言"
    },
    ms: {
        "app-title": "Portal Perkhidmatan Digital Kerajaan Singapura",
        "app-subtitle": "Akses direktori berkanun dan metrik data.gov.sg secara langsung dalam papan pemuka bersepadu.",
        "tab-portals": "Portal SG",
        "tab-hub": "Hab SG",
        "tab-whatsapp": "Simulator WhatsApp",
        "chat-disclaimer": "AI boleh membuat kesilapan dan ini bukan nasihat kewangan, cukai atau undang-undang. Sila semak semula jawapan dengan portal rasmi kerajaan sebelum bertindak.",
        "privacy-note": "Nota Privasi: Jangan muat naik kad pengenalan, pasport, penyata cukai atau penyata peribadi sensitif. Imej yang dimuat naik diproses oleh AI untuk analisis sahaja.",
        "suggest-bto": "BTO vs Resale",
        "suggest-journey": "SG Journey",
        "suggest-voting": "Undian ELD",
        "suggest-climate": "Baucar Iklim",
        "suggest-weather": "Cuaca/PSI",
        "suggest-jobs": "Kekosongan Kerja",
        "suggest-wages": "Gaji Pekerjaan AI",
        "document-copilot-title": "Copilot Dokumen",
        "document-copilot-desc": "Jana dan muat naik dokumen simulasi untuk menguji sistem penglihatan AI dan nasihat polisi.",
        "sim-noa": "Simulasikan IRAS Notice of Assessment",
        "sim-cpf": "Simulasikan Penyata CPF",
        "sim-payslip": "Simulasikan slip gaji bulanan",
        "elderly-mode-label": "Mod Warga Emas",
        "lang-label": "Bahasa"
    },
    ta: {
        "app-title": "சிங்கப்பூர் அரசு டிஜிட்டல் சேவைகள் போர்டல்",
        "app-subtitle": "அதிகாரப்பூர்வ அடைவுகள் மற்றும் நேரடி data.gov.sg அளவீடுகளை ஒருங்கிணைந்த டாஷ்போர்டில் அணுகவும்.",
        "tab-portals": "SG போர்ட்டல்கள்",
        "tab-hub": "SG ஹப்",
        "tab-whatsapp": "வாட்ஸ்அப் சிமுலேட்டர்",
        "chat-disclaimer": "AI தவறுகள் செய்யக்கூடும். இது நிதி, வரி அல்லது சட்ட ஆலோசனையல்ல. செயல்படுவதற்கு முன் அதிகாரப்பூர்வ அரசாங்க போர்ட்டல்களில் சரிபார்க்கவும்.",
        "privacy-note": "தனியுரிமைக் குறிப்பு: அடையாள அட்டைகள், பாஸ்போர்ட், வரி ஆவணங்கள் அல்லது தனிப்பட்ட ஆவணங்களைப் பதிவேற்ற வேண்டாம். பதிவேற்றப்படும் படங்கள் AI பகுப்பாய்விற்கு மட்டுமே பயன்படுத்தப்படும்.",
        "suggest-bto": "BTO vs மறுவிற்பனை",
        "suggest-journey": "சிங்கப்பூர் பயணம்",
        "suggest-voting": "ELD வாக்களிப்பு",
        "suggest-climate": "காலநிலை வவுச்சர்கள்",
        "suggest-weather": "வானிலை/PSI",
        "suggest-jobs": "வேலை வாய்ப்புகள்",
        "suggest-wages": "AI வேலை ஊதியம்",
        "document-copilot-title": "ஆவண உதவியாளர்",
        "document-copilot-desc": "ஏஐ பார்வை மற்றும் கொள்கை ஆலோசனைகளை சோதிக்க உருவகப்படுத்தப்பட்ட ஆவணங்களை உருவாக்கி பதிவேற்றவும்.",
        "sim-noa": "IRAS Notice of Assessment உருவகப்படுத்து",
        "sim-cpf": "CPF அறிக்கை உருவகப்படுத்து",
        "sim-payslip": "சம்பள சீட்டு உருவகப்படுத்து",
        "elderly-mode-label": "முதியோர் முறை",
        "lang-label": "மொழி"
    }
};

const WELCOME_MESSAGES = {
    en: {
        welcome1: "Welcome, Citizen. I am **MerlionOS**, your unified Singapore government assistant.",
        welcome2: "Ask me anything — e.g. *\"What are the HDB grant limits?\"* or *\"How much SkillsFuture credit do I have?\"* — and I'll look it up across all relevant agencies."
    },
    zh: {
        welcome1: "欢迎您，公民。我是 **MerlionOS**，您的统一新加坡政府助理。",
        welcome2: "您可以问我任何问题 —— 例如 *“HDB 购房津贴限额是多少？”* 或 *“我还有多少 SkillsFuture 培训补助金？”* —— 我会帮您在所有相关机构中查询。"
    },
    ms: {
        welcome1: "Selamat datang, Warganegara. Saya **MerlionOS**, pembantu kecerdasan buatan bersepadu bagi sektor awam Singapura.",
        welcome2: "Tanya saya apa-apa sahaja — cth. *\"Apakah had geran perumahan HDB?\"* atau *\"Berapakah baki kredit SkillsFuture saya?\"* — dan saya akan menyemaknya di semua agensi berkaitan."
    },
    ta: {
        welcome1: "வரவேற்கிறோம், குடிமக்களே. நான் **மெர்லியன்ஓஎஸ்** (MerlionOS), சிங்கப்பூர் அரசாங்கத்தின் ஒருங்கிணைந்த AI உதவியாளர்.",
        welcome2: "என்னிடம் ஏதேனும் கேளுங்கள் — எ.கா. *\"HDB மானிய வரம்புகள் என்ன?\"* அல்லது *\"எனது SkillsFuture கிரெடிட் எவ்வளவு?\"* — நான் அனைத்து ஏஜென்சிகளிலும் தேடி பதிலளிப்பேன்."
    }
};

// Global language and elderly state
let currentLanguage = localStorage.getItem("merlion_language") || "en";
let elderlyModeActive = localStorage.getItem("merlion_elderly_mode") === "true";

function translateUI(lang = currentLanguage) {
    currentLanguage = lang;
    window.currentLanguage = lang;
    localStorage.setItem("merlion_language", lang);

    // 1. Translate all data-translate elements
    const elements = document.querySelectorAll("[data-translate]");
    elements.forEach(el => {
        const key = el.getAttribute("data-translate");
        if (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) {
            el.innerHTML = TRANSLATIONS[lang][key];
        }
    });

    // 2. Translate suggestion chips data-query attributes (dynamic prompts)
    const chips = document.querySelectorAll(".suggestion-chip");
    const langQueries = {
        en: {
            "BTO vs Resale": "What's the difference between a BTO and a resale flat, and what CPF housing grants can I get?",
            "SG Journey": "What are the requirements for the Singapore Journey onboarding?",
            "ELD Voting": "How do I check my electoral voting status with ELD?",
            "Climate Vouchers": "What are the Climate Vouchers and how do I claim them from gov.sg?",
            "Weather/PSI": "Check live weather forecast and air quality PSI index",
            "Job Vacancies": "Analyse tech industry job vacancies, YoY trend, and next-year forecast",
            "AI Job Wages": "Which new AI job titles appeared in Singapore's occupational wage tables this year, and what do they pay?"
        },
        zh: {
            "BTO vs Resale": "组屋与转售屋有什么区别，我可以获得哪些公积金购房津贴？",
            "SG Journey": "新加坡公民入籍“新加坡之旅”有哪些要求？",
            "ELD Voting": "我该如何向选举局检查我的选民投票资格和状态？",
            "Climate Vouchers": "什么是新加坡气候优惠券，我该如何从 gov.sg 申领？",
            "Weather/PSI": "查询新加坡实时天气预报和空气污染 PSI 指数",
            "Job Vacancies": "分析科技行业的职位空缺、同比趋势和明年预测",
            "AI Job Wages": "今年新加坡职业薪资表中新增了哪些 AI 职位，薪资是多少？"
        },
        ms: {
            "BTO vs Resale": "Apakah perbezaan antara flat BTO dan flat resale, dan apakah geran perumahan CPF yang boleh saya dapat?",
            "SG Journey": "Apakah syarat-syarat bagi kemasukan Singapore Journey?",
            "ELD Voting": "Bagaimanakah saya boleh menyemak status undian pilihan raya saya dengan ELD?",
            "Climate Vouchers": "Apakah Baucar Iklim dan bagaimanakah cara untuk menuntutnya daripada gov.sg?",
            "Weather/PSI": "Semak ramalan cuaca langsung dan indeks PSI kualiti udara",
            "Job Vacancies": "Analisis kekosongan jawatan industri teknologi, trend YoY, dan ramalan tahun depan",
            "AI Job Wages": "Apakah jawatan kerja AI baru yang muncul dalam jadual gaji pekerjaan Singapura tahun ini, dan berapakah gajinya?"
        },
        ta: {
            "BTO vs Resale": "BTO மற்றும் மறுவிற்பனை பிளாட் இடையே உள்ள வேறுபாடு என்ன, என்ன CPF வீட்டு மானியங்களை நான் பெறலாம்?",
            "SG Journey": "சிங்கப்பூர் ஜர்னி (Singapore Journey) சேர்க்கைக்கான தேவைகள் யாவை?",
            "ELD Voting": "ELD மூலம் எனது தேர்தல் வாக்களிப்பு நிலையை எவ்வாறு சரிபார்க்கலாம்?",
            "Climate Vouchers": "காலநிலை வவுச்சர்கள் என்றால் என்ன மற்றும் gov.sg இலிருந்து அவற்றை எவ்வாறு கோரலாம்?",
            "Weather/PSI": "நேரடி வானிலை முன்னறிவிப்பு மற்றும் காற்றின் தரம் PSI குறியீட்டை சரிபார்க்கவும்",
            "Job Vacancies": "தொழில்நுட்பத் துறை வேலை காலியிடங்கள், YoY போக்கு மற்றும் அடுத்த ஆண்டு முன்னறிவிப்பை பகுப்பாய்வு செய்க",
            "AI Job Wages": "இந்த ஆண்டு சிங்கப்பூர் வேலை ஊதிய அட்டவணையில் என்ன புதிய AI வேலைப் பெயர்கள் தோன்றின, அவை எவ்வளவு செலுத்துகின்றன?"
        }
    };

    chips.forEach(chip => {
        const textKey = chip.textContent.trim();
        // Translate text inside chip
        const chipTranslations = {
            en: { "BTO vs Resale": "BTO vs Resale", "SG Journey": "SG Journey", "ELD Voting": "ELD Voting", "Climate Vouchers": "Climate Vouchers", "Weather/PSI": "Weather/PSI", "Job Vacancies": "Job Vacancies", "AI Job Wages": "AI Job Wages" },
            zh: { "BTO vs Resale": "组屋 vs 转售屋", "SG Journey": "新加坡之旅", "ELD Voting": "选民资格", "Climate Vouchers": "环保券", "Weather/PSI": "天气/PSI", "Job Vacancies": "职位分析", "AI Job Wages": "AI薪水" },
            ms: { "BTO vs Resale": "BTO vs Resale", "SG Journey": "SG Journey", "ELD Voting": "Undian ELD", "Climate Vouchers": "Baucar Iklim", "Weather/PSI": "Cuaca/PSI", "Job Vacancies": "Kerja Kosong", "AI Job Wages": "Gaji AI" },
            ta: { "BTO vs Resale": "BTO vs மறுவிற்பனை", "SG Journey": "சிங்கப்பூர் பயணம்", "ELD Voting": "ELD வாக்களிப்பு", "Climate Vouchers": "Baucar Iklim", "Weather/PSI": "வானிலை/PSI", "Job Vacancies": "வேலைகள்", "AI Job Wages": "AI சம்பளம்" }
        };

        // Find standard key
        let standardKey = null;
        for (const [k, v] of Object.entries(chipTranslations.en)) {
            if (chip.getAttribute("data-query") === langQueries.en[k] || chip.textContent.includes(v)) {
                standardKey = k;
                break;
            }
        }
        if (!standardKey) return;

        // Apply translations
        if (chipTranslations[lang] && chipTranslations[lang][standardKey]) {
            chip.textContent = chipTranslations[lang][standardKey];
        }
        if (langQueries[lang] && langQueries[lang][standardKey]) {
            chip.setAttribute("data-query", langQueries[lang][standardKey]);
        }
    });

    // 3. Update active elements UI selection (sync headers, dropdown lists)
    document.querySelectorAll(".current-lang-text").forEach(el => {
        const langNames = { en: "English", zh: "中文", ms: "Melayu", ta: "தமிழ்" };
        el.textContent = langNames[lang] || "English";
    });

    // 4. Update the Welcome message in the chat widget if the chat hasn't started yet
    const chatMsgs = document.getElementById("chat-messages");
    if (chatMsgs && chatMsgs.dataset.conversationStarted !== "true") {
        const welObj = WELCOME_MESSAGES[lang] || WELCOME_MESSAGES.en;
        chatMsgs.innerHTML = `
            <div class="message bot-message">
                <div class="message-avatar"><i class="fa-solid fa-landmark"></i></div>
                <div class="message-content">
                    <p>${renderMarkdown(welObj.welcome1)}</p>
                    <p>${renderMarkdown(welObj.welcome2)}</p>
                </div>
            </div>
        `;
    }
}

function toggleElderlyMode(active) {
    elderlyModeActive = active;
    window.elderlyModeActive = active;
    localStorage.setItem("merlion_elderly_mode", active ? "true" : "false");

    if (active) {
        document.body.classList.add("elderly-mode");
    } else {
        document.body.classList.remove("elderly-mode");
    }

    // Sync all toggle switch inputs
    document.querySelectorAll(".elderly-mode-toggle").forEach(el => {
        el.checked = active;
    });
}

// Helper: Lightweight markdown formatter (bold and italics)
function renderMarkdown(txt) {
    if (!txt) return "";
    return txt
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<em>$1</em>")
        .replace(/`([^`]+)`/g, "<code>$1</code>");
}

// Bootstrap languages and elderly mode on window load
window.addEventListener("DOMContentLoaded", () => {
    // 1. Language selector dropdown
    const langBtn = document.getElementById("lang-select-btn");
    const langMenu = document.getElementById("lang-menu");
    
    if (langBtn && langMenu) {
        langBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            langMenu.classList.toggle("hidden");
            langBtn.setAttribute("aria-expanded", !langMenu.classList.contains("hidden"));
        });
        
        document.addEventListener("click", () => {
            langMenu.classList.add("hidden");
            langBtn.setAttribute("aria-expanded", "false");
        });
        
        langMenu.querySelectorAll(".lang-menu-item").forEach(item => {
            item.addEventListener("click", () => {
                const lang = item.getAttribute("data-lang");
                if (lang) {
                    translateUI(lang);
                    // Update selection highlights
                    langMenu.querySelectorAll(".lang-menu-item").forEach(i => i.classList.remove("selected"));
                    item.classList.add("selected");
                }
            });
        });
        
        // Highlight current language on load
        const activeItem = langMenu.querySelector(`[data-lang="${currentLanguage}"]`);
        if (activeItem) activeItem.classList.add("selected");
    }
    
    // 2. Elderly mode toggles
    document.querySelectorAll(".elderly-mode-toggle").forEach(toggle => {
        toggle.addEventListener("change", (e) => {
            toggleElderlyMode(e.target.checked);
        });
    });
    
    // Initialize switch state
    document.querySelectorAll(".elderly-mode-toggle").forEach(toggle => {
        toggle.checked = elderlyModeActive;
    });

    // Read from state and initialize
    translateUI(currentLanguage);
    toggleElderlyMode(elderlyModeActive);
});
