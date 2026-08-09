// translations.js — Manage multilingual localization (EN, ZH, MS, TA)
// and elderly accessibility/large-text mode settings on the frontend.

const TRANSLATIONS = {
    en: {
        "app-title": "Singapore Government Digital Services Portal",
        "app-subtitle": "Access statutory directories and live data.gov.sg metrics in a unified dashboard.",
        "tab-portals": "SG Portals",
        "tab-hub": "SG Hub",
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
        "lang-label": "Language",
        "reorder-hint": "Drag any card to rearrange your portal — hover a card and click the eye icon to hide it.",
        "btn-sort": "Sort",
        "btn-show-all": "Show all",
        "btn-hide-all": "Hide all",
        "btn-reset-layout": "Reset layout",
        "btn-manage-portals": "Manage Portals",
        "my-matters-title": "My Matters",
        "my-matters-pinned": "Pinned",
        "my-matters-hint": "Your bookmarked portals — click ★ on any card to pin it here",
        "my-matters-clear": "Clear all",
        "all-portals-title": "All Statutory Portals",
        "portal-search-placeholder": 'What do you need? Try "renew passport", "pay road tax", "change company address"...',
        "active-engine-label": "Active Engine",
        "onboarding-title": "Welcome to MerlionOS — Singapore's AI-powered public service brain",
        "onboarding-feat1": 'Search 30+ agencies in plain English — <em>"renew passport"</em>, <em>"top up CPF"</em>',
        "onboarding-feat2": "Ask the AI Copilot any government question and get cited, actionable answers",
        "onboarding-feat3": "Live dashboards — MRT status, PSI, BTO launches, job market & COE trends",
        "onboarding-dismiss": "Got it",
        "chat-input-placeholder": "Type query or paste gov.sg URL...",
        "card-link-text": "Go to Portal",
        "drawer-tab-assistant": "Assistant",
        "drawer-tab-logs": "Operations Trace",
        "hub-card-panels-label": "Card Panels:",
        "hub-collapse-hint": "(Click any card title to collapse/expand)",
        "hub-btn-collapse-all": "Collapse All",
        "hub-btn-expand-all": "Expand All",
        "hub-sub-tab-life-events": "Life Events",
        "hub-sub-tab-transport": "Transit & Transport",
        "hub-sub-tab-gov-updates": "Gov Updates",
        "hub-sub-tab-hdb": "HDB & BTO Portal",
        "hub-sub-tab-jobs": "Job Market Analysis",
        "hub-sub-tab-tax": "IRAS Tax & Wealth",
        "hub-sub-tab-deals": "Kiasu Deals",
        "hub-sub-tab-env": "Weather & PSI",
        "hub-sub-tab-alerts": "My Alerts",
        "hub-sub-tab-scam": "Scam Checker",
        "hub-sub-tab-benefits": "Benefits Finder",
        "hub-sub-tab-home-cost": "Home Cost",
        "hub-sub-tab-cpf-life": "CPF LIFE",
        "panel-transit-delays-title": "Transit Delays & Traffic Advisories",
        "panel-transit-delays-desc": "Real-time MRT delay reports, train disruptions, and road alerts from LTA & SMRT channels.",
        "panel-taxi-title": "Taxis Available Islandwide",
        "panel-taxi-desc": "Live taxi availability counts, location-based nearby taxis, and real-time positions map (LTA DataMall).",
        "panel-coe-title": "Transport & Vehicle Costs (COE)",
        "panel-coe-desc": "Latest COE bidding premiums by vehicle category and multi-year trend analysis (data.gov.sg).",
        "panel-ica-title": "ICA Checkpoint & News Updates",
        "panel-ica-desc": "Real-time advisories, media releases, and checkpoint updates fetched directly from the ICA Newsroom."
    },
    zh: {
        "app-title": "新加坡政府数字化服务门户",
        "app-subtitle": "在统一的控制面板中访问法定名录和实时 data.gov.sg 指标。",
        "tab-portals": "新加坡门户",
        "tab-hub": "新加坡中心",
        "chat-disclaimer": "AI 可能会犯错，此内容不构成财务、税务或法律建议。在采取行动之前，请先登录官方政府门户网站复核。",
        "privacy-note": "隐私提示：请勿上传身份证、护照、报税单或敏感个人账单。上传的图片仅供 AI 分析处理。",
        "suggest-bto": "预购组屋 vs 转售组屋",
        "suggest-journey": "新加坡之旅",
        "suggest-voting": "选民登记查询",
        "suggest-climate": "绿色环保券",
        "suggest-weather": "天气与 PSI 指数",
        "suggest-jobs": "行业职位分析",
        "suggest-wages": "AI 职位薪资",
        "document-copilot-title": "文档副驾驶",
        "document-copilot-desc": "生成并上传模拟文件，测试多模态视觉与政策建议引擎。",
        "sim-noa": "模拟 IRAS 缴税通知单 (NOA)",
        "sim-cpf": "模拟 CPF 结单",
        "sim-payslip": "模拟每月薪水单",
        "elderly-mode-label": "老年模式",
        "lang-label": "语言",
        "reorder-hint": "拖动任何卡片重新排列您的门户 — 将鼠标悬停在卡片上并点击眼睛图标以隐藏。",
        "btn-sort": "排序",
        "btn-show-all": "显示全部",
        "btn-hide-all": "隐藏全部",
        "btn-reset-layout": "重置布局",
        "btn-manage-portals": "管理门户",
        "my-matters-title": "我的常用门户",
        "my-matters-pinned": "已钉选",
        "my-matters-hint": "您书签标记的常用门户 — 点击任意卡片上的 ★ 图标钉选至此处",
        "my-matters-clear": "清除全部",
        "all-portals-title": "所有法定机构门户",
        "portal-search-placeholder": '您需要办理什么业务？试试 “更新护照”、“缴纳路税”、“变更公司地址”...',
        "active-engine-label": "引擎运行中",
        "onboarding-title": "欢迎使用 MerlionOS — 新加坡人工智能公共服务智慧大脑",
        "onboarding-feat1": '用日常语言搜索 30+ 政府机构 — 如“更新护照”、“充值 CPF”',
        "onboarding-feat2": "向 AI 副驾驶询问任何政府事务，获取有据可查的针对性解答",
        "onboarding-feat3": "实时控制面板 — 地铁状态、PSI 指数、BTO 组屋发售、就业市场与拥屋证趋势",
        "onboarding-dismiss": "知道了",
        "chat-input-placeholder": "输入提问或粘贴 gov.sg 网址...",
        "card-link-text": "前往门户",
        "drawer-tab-assistant": "智能助手",
        "drawer-tab-logs": "运行日志",
        "hub-card-panels-label": "功能卡片面板：",
        "hub-collapse-hint": "(点击任意卡片标题展开/折叠)",
        "hub-btn-collapse-all": "全部折叠",
        "hub-btn-expand-all": "全部展开",
        "hub-sub-tab-life-events": "人生阶段",
        "hub-sub-tab-transport": "交通与出行",
        "hub-sub-tab-gov-updates": "政府公告",
        "hub-sub-tab-hdb": "HDB 与 BTO 门户",
        "hub-sub-tab-jobs": "就业市场分析",
        "hub-sub-tab-tax": "IRAS 税务与财富",
        "hub-sub-tab-deals": "生活优惠",
        "hub-sub-tab-env": "天气与 PSI",
        "hub-sub-tab-alerts": "我的预警",
        "hub-sub-tab-scam": "诈骗检测",
        "hub-sub-tab-benefits": "福利津贴",
        "hub-sub-tab-home-cost": "购房成本",
        "hub-sub-tab-cpf-life": "CPF 年金",
        "panel-transit-delays-title": "地铁延迟与交通公告",
        "panel-transit-delays-desc": "来自陆路交通局 (LTA) 及 SMRT 的实时地铁延迟报告、列车中断和道路警报。",
        "panel-taxi-title": "全岛德士实时数量",
        "panel-taxi-desc": "实时德士数量、基于位置的周边德士及实时位置地图 (LTA DataMall)。",
        "panel-coe-title": "交通与拥屋证成本 (COE)",
        "panel-coe-desc": "各车组最新拥屋证 (COE) 投标价格与多年趋势分析 (data.gov.sg)。",
        "panel-ica-title": "ICA 关卡与新闻更新",
        "panel-ica-desc": "直接从移民与关卡局 (ICA) 新闻室获取的实时通告、新闻稿及通关更新。"
    },
    ms: {
        "app-title": "Portal Perkhidmatan Digital Kerajaan Singapura",
        "app-subtitle": "Akses direktori berkanun dan metrik data.gov.sg secara langsung dalam papan pemuka bersepadu.",
        "tab-portals": "Portal SG",
        "tab-hub": "Hab SG",
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
        "lang-label": "Bahasa",
        "reorder-hint": "Seret mana-mana kad untuk menyusun semula portal anda — lalukan kursor dan klik ikon mata untuk menyembunyikan.",
        "btn-sort": "Susun",
        "btn-show-all": "Tunjukkan semua",
        "btn-hide-all": "Sembunyikan semua",
        "btn-reset-layout": "Set semula susunan",
        "btn-manage-portals": "Urus Portal",
        "my-matters-title": "Perkara Saya",
        "my-matters-pinned": "Disematkan",
        "my-matters-hint": "Portal penanda halaman anda — klik ★ pada mana-mana kad untuk menyematkannya di sini",
        "my-matters-clear": "Kosongkan semua",
        "all-portals-title": "Semua Portal Berkanun",
        "portal-search-placeholder": 'Apakah yang anda perlukan? Cuba "perbaharui pasport", "bayar cukai jalan"...',
        "active-engine-label": "Enjin Aktif",
        "onboarding-title": "Selamat datang ke MerlionOS — Otak perkhidmatan awam berasaskan AI Singapura",
        "onboarding-feat1": 'Cari 30+ agensi dalam bahasa mudah — "perbaharui pasport", "tambah nilai CPF"',
        "onboarding-feat2": "Tanya AI Copilot apa-apa soalan kerajaan dan dapatkan jawapan bertanda rujukan",
        "onboarding-feat3": "Papan pemuka langsung — status MRT, PSI, BTO, pasaran kerja & trend COE",
        "onboarding-dismiss": "Faham",
        "chat-input-placeholder": "Taip soalan atau tampal URL gov.sg...",
        "card-link-text": "Ke Portal",
        "drawer-tab-assistant": "Pembantu",
        "drawer-tab-logs": "Jejak Operasi",
        "hub-card-panels-label": "Panel Kad:",
        "hub-collapse-hint": "(Klik tajuk kad untuk menutup/membuka)",
        "hub-btn-collapse-all": "Tutup Semua",
        "hub-btn-expand-all": "Buka Semua",
        "hub-sub-tab-life-events": "Peristiwa Kehidupan",
        "hub-sub-tab-transport": "Transit & Pengangkutan",
        "hub-sub-tab-gov-updates": "Kemaskini Kerajaan",
        "hub-sub-tab-hdb": "Portal HDB & BTO",
        "hub-sub-tab-jobs": "Analisis Pasaran Kerja",
        "hub-sub-tab-tax": "Cukai & Kekayaan IRAS",
        "hub-sub-tab-deals": "Tawaran Kiasu",
        "hub-sub-tab-env": "Cuaca & PSI",
        "hub-sub-tab-alerts": "Amaran Saya",
        "hub-sub-tab-scam": "Pemeriksa Penipuan",
        "hub-sub-tab-benefits": "Pencari Manfaat",
        "hub-sub-tab-home-cost": "Kos Rumah",
        "hub-sub-tab-cpf-life": "CPF LIFE",
        "panel-transit-delays-title": "Kelewatan Transit & Nasihat Trafik",
        "panel-transit-delays-desc": "Laporan kelewatan MRT masa nyata, gangguan tren, dan amaran jalan raya dari saluran LTA & SMRT.",
        "panel-taxi-title": "Teksi Tersedia Seluruh Negara",
        "panel-taxi-desc": "Kiraan ketersediaan teksi langsung, teksi berdekatan berdasarkan lokasi, dan peta kedudukan masa nyata (LTA DataMall).",
        "panel-coe-title": "Kos Pengangkutan & Kenderaan (COE)",
        "panel-coe-desc": "Premium bidaan COE terkini mengikut kategori kenderaan dan analisis trend pelbagai tahun (data.gov.sg).",
        "panel-ica-title": "Pusat Pemeriksaan & Berita ICA",
        "panel-ica-desc": "Nasihat masa nyata, siaran media, dan kemaskini pusat pemeriksaan dari Bilik Berita ICA."
    },
    ta: {
        "app-title": "சிங்கப்பூர் அரசு டிஜிட்டல் சேவைகள் போர்டல்",
        "app-subtitle": "அதிகாரப்பூர்வ அடைவுகள் மற்றும் நேரடி data.gov.sg அளவீடுகளை ஒருங்கிணைந்த டாஷ்போர்டில் அணுகவும்.",
        "tab-portals": "SG போர்ட்டல்கள்",
        "tab-hub": "SG ஹப்",
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
        "lang-label": "மொழி",
        "reorder-hint": "உங்கள் போர்ட்டலை மாற்றியமைக்க எந்த கார்டையும் இழுக்கவும் — மறைக்க கண் ஐகானைக் கிளிக் செய்யவும்.",
        "btn-sort": "வரிசைப்படுத்து",
        "btn-show-all": "அனைத்தையும் காட்டு",
        "btn-hide-all": "அனைத்தையும் மறை",
        "btn-reset-layout": "அமைப்பை மீட்டமை",
        "btn-manage-portals": "போர்ட்டல்களை நிர்வகி",
        "my-matters-title": "என் விவகாரங்கள்",
        "my-matters-pinned": "ஒட்டப்பட்டது",
        "my-matters-hint": "உங்கள் புக்மார்க் செய்யப்பட்ட போர்ட்டல்கள் — இங்கே ஒட்ட எந்த கார்டிலும் ★ கிளிக் செய்யவும்",
        "my-matters-clear": "அனைத்தையும் அழி",
        "all-portals-title": "அனைத்து போர்ட்டல்கள்",
        "portal-search-placeholder": 'உங்களுக்கு என்ன வேண்டும்? "பாஸ்போர்ட் புதுப்பித்தல்", "சாலை வரி செலுத்த"...',
        "active-engine-label": "இயங்கும் எஞ்சின்",
        "onboarding-title": "MerlionOS-க்கு வரவேற்கிறோம் — சிங்கப்பூரின் AI பொது சேவை மூளை",
        "onboarding-feat1": 'எளிய மொழியில் 30+ ஏஜென்சிகளைத் தேடுங்கள் — "பாஸ்போர்ட் புதுப்பித்தல்", "CPF டாப் அப்"',
        "onboarding-feat2": "AI Copilot-மிடம் ஏதேனும் கேள்விகளைக் கேட்டு சான்றளிக்கப்பட்ட பதில்களைப் பெறுங்கள்",
        "onboarding-feat3": "நேரடி டாஷ்போர்டுகள் — MRT நிலை, PSI, BTO, வேலை சந்தை & COE போக்குகள்",
        "onboarding-dismiss": "புரிந்தது",
        "chat-input-placeholder": "கேள்வியை டைப் செய்யவும் அல்லது gov.sg URL ஒட்டவும்...",
        "card-link-text": "போர்ட்டலுக்குச் செல்",
        "drawer-tab-assistant": "உதவியாளர்",
        "drawer-tab-logs": "இயக்கப் பதிவு",
        "hub-card-panels-label": "கார்டு பேனல்கள்:",
        "hub-collapse-hint": "(சுருக்க/விரிவாக்க தலைப்பைக் கிளிக் செய்க)",
        "hub-btn-collapse-all": "அனைத்தும் சுருக்கு",
        "hub-btn-expand-all": "அனைத்தும் விரி",
        "hub-sub-tab-life-events": "வாழ்க்கை நிகழ்வுகள்",
        "hub-sub-tab-transport": "போக்குவரத்து",
        "hub-sub-tab-gov-updates": "அரசு செய்திகள்",
        "hub-sub-tab-hdb": "HDB & BTO போர்டல்",
        "hub-sub-tab-jobs": "வேலை சந்தை பகுப்பாய்வு",
        "hub-sub-tab-tax": "IRAS வரி & செல்வம்",
        "hub-sub-tab-deals": "சலுகைகள்",
        "hub-sub-tab-env": "வானிலை & PSI",
        "hub-sub-tab-alerts": "எனது விழிப்பூட்டல்கள்",
        "hub-sub-tab-scam": "மோசடி சரிபார்ப்பு",
        "hub-sub-tab-benefits": "நலத்திட்ட தேடல்கள்",
        "hub-sub-tab-home-cost": "வீட்டு செலவு",
        "hub-sub-tab-cpf-life": "CPF LIFE",
        "panel-transit-delays-title": "போக்குவரத்து தாமதங்கள் & அறிவிப்புகள்",
        "panel-transit-delays-desc": "LTA மற்றும் SMRT சேனல்களிலிருந்து நேரடி MRT தாமத அறிக்கைகள் மற்றும் சாலை விழிப்பூட்டல்கள்.",
        "panel-taxi-title": "தீவு முழுவதும் டாக்சிகள்",
        "panel-taxi-desc": "நேரடி டாக்சி கிடைப்பு எண்ணிக்கைகள் மற்றும் இருப்பிட அடிப்படையிலான டாக்சிகள் வரைபடம் (LTA DataMall).",
        "panel-coe-title": "வாகன செலவுகள் (COE)",
        "panel-coe-desc": "வாகன வகை மற்றும் பல ஆண்டு போக்கு பகுப்பாய்வு மூலம் சமீபத்திய COE ஏல பிரீமியங்கள் (data.gov.sg).",
        "panel-ica-title": "ICA சோதனைச் சாவடி செய்திகள்",
        "panel-ica-desc": "ICA செய்தி அறையிலிருந்து நேரடியாகப் பெறப்பட்ட நேரடி அறிவிப்புகள் மற்றும் செய்தி வெளியீடுகள்."
    }
};

const AGENCY_DESCRIPTIONS = {
    zh: {
        ica: "公民身份、护照更新及 MyICA 预约服务。",
        eld: "查询选民登记状态与选民名册。",
        iras: "个人所得税申报、房产税及消费税 (GST) 记录。",
        cpf: "退休储蓄、MediSave 账户及雇主公积金缴存。",
        redeemsg: "兑换家庭社理会消费券 (CDC Vouchers) 及绿色优惠券。",
        govbenefits: "查询资格并领取定心与支援套餐、GST 消费税补助券及国民服役现金发放。",
        spgroup: "开通水电燃气账户及查询消费回扣状态。",
        skillsfuture: "使用 S$500 技能创前程培训补助及职业津贴。",
        wsg: "搜索新加坡职位空缺、参加中途职业转换计划 (PCP) 及职业指导。",
        mom: "工作准证 (Work Permit/EP/SPass)、雇佣法则及劳工法条规。",
        moh: "HealthHub 应用程序、全国健康电子纪录 (NEHR) 及综合诊疗所补贴。",
        hdb: "预购组屋 (BTO) 申请、购房津贴及 HDB 贷款限额。",
        moe: "小学/中学入学报名、学费及奖学金申请。",
        lta: "OneMotoring 账户、COE 拥屋证竞标、路税及公共交通图。",
        nea: "气候优惠券指南、实时天气 PSI 烟霾指数及餐饮卫生评级。",
        govsg: "新加坡内阁政策公告、财政预算案与官方新闻。",
        sgjourney: "新公民入籍“新加坡之旅”在线培训与活动登记。",
        onemap: "权威地理地图、学校距离与选区范围查询。",
        healthhub: "医疗预约、诊疗纪录、药物续配及健康检查报告。",
        activesg: "体育馆、游泳池、羽毛球场预订及免费 ActiveSG 积分。",
        hpb: "Healthy 365 步数奖励计划、健康筛查与疫苗接种。",
        msf: "ComCare 社会援助、婴儿育儿花红及托儿津贴申请。",
        pub: "水费账单、排水防洪预警及节约用水回扣。",
        nlb: "国家图书馆借书、电子书及自习室预订。",
        ura: "城市规划发展蓝图、保留建筑物与公共停车场。",
        nparks: "烧烤台、露营许可证预订及国家公园指导。",
        mas: "新加坡储蓄债券 (SSB)、国库券 (T-bill) 及金融监管。",
        imda: "防诈骗短信 Sender ID 登记及电信服务投诉。",
        ns: "国民服役 (NS) 状态、战备军人出境许可证及回归登记。",
        spf: "警局无犯罪记录证明、交通罚款及防诈骗报案。",
        scdf: "防火安全认证、民防救护车及 CPR/AED myResponder 应用。",
        acra: "注册公司业务、BizFile 年检申报及变更公司登记地址。",
        enterprisesg: "中小企业 (SME) 商业津贴、PSG 与 EDG 发展补助。",
        ipos: "商标、专利、品牌著作权及知识产权保护。",
        sla: "土地地契、房产所有权 INLIS 查询及国有土地租赁。",
        cea: "房地产经纪 (Property Agent) 牌照与合规查询。",
        pa: "民众俱乐部 (CC) 课程、兴趣小组及 Passion 卡。",
        mindef: "国防部、武装部队及军事实务。",
        seab: "PSLE、O水准、A水准考试成绩及私人考生登记。",
        judiciary: "新加坡法院听证会及小额赔偿法庭 (Small Claims Tribunal)。",
        mlaw: "离婚、遗嘱继承、法律援助及破产管理。",
        sgenable: "残疾辅助津贴、辅助技术及特需人群支持。",
        mfa: "海外旅游安全警示、使领馆及行程登记 (eRegister)。",
        sfa: "食品安全召回、进口许可证及家庭小吃营业许可。",
        gra: "赌场入场费、禁入令及赌博监管。",
        nac: "街头表演 (Busking) 许可证及艺术活动资助。",
        mccy: "慈善机构捐款、志愿服务及青年活动。",
        rom: "婚姻注册 (ROM/ROMM)、婚礼预订及结婚证书。",
        csa: "ScamShield 防诈骗防护、网络安全警示及举报钓鱼网站。",
        aic: "护老院、居家护理补贴及银发族护工支持。",
        muis: "清真认证 (Halal Cert)、天课 (Zakat) 及清真寺活动。",
        ssg: "技能创前程培训课程资助及 WSQ 职业资格认证。",
        sportsg: "新加坡国家运动代表队、体育发展及教练认证。",
        pdpc: "个人资料保护法 (PDPA)、谢绝来电登记处 (DNC Registry)。",
        cnb: "中央肃毒局、戒毒康复及防毒教育。",
        sps: "监狱探监预约、黄丝带计划 (Yellow Ribbon Project) 重返社会。",
        tadm: "劳资政纠纷调解 (TADM)、追讨欠薪及解雇咨询。",
        tafep: "劳资政公平雇佣法条 (TAFEP)、职场歧视与抗骚扰投诉。"
    },
    ms: {
        ica: "Status kewarganegaraan, pembaruan pasport, dan janji temu MyICA.",
        eld: "Semak status pendaftaran pengundi dan daftar pemilih.",
        iras: "Fail cukai pendapatan peribadi, cukai hartanah, dan akaun GST.",
        cpf: "Simpanan persaraan, akaun MediSave, dan caruman majikan.",
        redeemsg: "Tuntut baucar CDC isi rumah dan rebat iklim.",
        govbenefits: "Semak kelayakan dan terima Pakej Jaminan, Baucar GST, dan baucar NS.",
        spgroup: "Buka akaun elektrik, air, dan gas serta semak status rebat.",
        skillsfuture: "Akses kredit kemahiran S$500 dan subsidi kursus.",
        wsg: "Cari kerja Singapura, akaun program pertukaran kerjaya (PCP).",
        mom: "Pas kerja, undang-undang pekerjaan, dan perkhidmatan pas kerja.",
        moh: "Aplikasi HealthHub, rekod perubatan NEHR, dan poliklinik subsidi.",
        hdb: "Permohonan flat BTO, geran perumahan, dan had pinjaman HDB.",
        moe: "Pendaftaran sekolah rendah/menengah dan biasiswa pengajian.",
        lta: "Akaun OneMotoring, bidaan COE, cukai jalan, dan peta transit.",
        nea: "Panduan baucar iklim, ramalan cuaca PSI, dan gred kebersihan makanan.",
        govsg: "Pengumuman dasar kerajaan, Belanjawan, dan berita rasmi.",
        sgjourney: "Latihan dan acara Singapore Journey bagi warganegara baru.",
        onemap: "Peta rasmi Singapura, jarak sekolah, dan sempadan kawasang undi.",
        healthhub: "Temujanji perubatan, rekod pesakit, dan keputusannya.",
        activesg: "Tempahan gim, kolam renang, gelanggang sukan & kredit percuma.",
        hpb: "Cabaran Healthy 365, ganjaran langkah, dan pemeriksaan kesihatan.",
        msf: "Bantuan ComCare, Bonus Bayi, dan subsidi penjagaan anak.",
        pub: "Bil air, amaran banjir, dan rebat penjimatan air.",
        nlb: "Pinjam buku perpustakaan, e-buku, dan tempahan bilik belajar.",
        ura: "Pelan induk pembangunan bandar dan tempat letak kereta awam.",
        nparks: "Tempahan tapak barbeku, permit perkhemahan, dan taman negara.",
        mas: "Bon Simpanan Singapura (SSB), Bil Perbendaharaan (T-bill).",
        imda: "Pendaftaran ID Penghantar SMS dan aduan telekomunikasi.",
        ns: "Status Perkhidmatan Negara (NS), permit keluar, dan pendaftaran.",
        spf: "Sijil kelakuan baik polis, saman trafik, dan aduan penipuan.",
        scdf: "Sijil keselamatan kebakaran, ambulans, dan aplikasi myResponder.",
        acra: "Pendaftaran syarikat, penyata tahunan BizFile, dan tukar alamat.",
        enterprisesg: "Geran perniagaan PKS (SME), geran PSG dan EDG.",
        ipos: "Cap dagangan, paten, hak cipta, dan perlindungan harta intelek.",
        sla: "Surat hak milik tanah, kepemilikan hartanah INLIS.",
        cea: "Semakan lesen ejen hartanah dan aduan.",
        pa: "Kursus Kelab Masyarakat (CC), kumpulan minat, dan kad PAssion.",
        mindef: "Kementerian Pertahanan, Angkatan Tentera Singapura (SAF).",
        seab: "Keputusan peperiksaan PSLE, GCE O/A Level.",
        judiciary: "Mahkamah Singapura dan Tribunal Tuntutan Kecil.",
        mlaw: "Perceraian, wasiat, bantuan guaman, dan kebankrapan.",
        sgenable: "Sokongan kurang upaya, teknologi bantuan, dan keperluan khas.",
        mfa: "Nasihat perjalanan luar negara dan eRegister.",
        sfa: "Keselamatan makanan, lesen import, dan makanan buatan rumah.",
        gra: "Levu masuk kasino dan sekatan perjudian.",
        nac: "Lesen persembahan jalanan (busking) dan geran seni.",
        mccy: "Derma kebajikan, sukarelawan, dan aktiviti belia.",
        rom: "Pendaftaran perkahwinan (ROM/ROMM) dan tempahan tempoh nikah.",
        csa: "Perlindungan penipuan ScamShield dan amaran keselamatan siber.",
        aic: "Bantuan pusat penjagaan warga emas dan subsidi penjaga.",
        muis: "Pensijilan Halal, zakat fitrah, haji, dan aktiviti masjid.",
        ssg: "Kredit SkillsFuture dan akreditasi kelayakan WSQ.",
        sportsg: "Pembangunan sukan kebangsaan dan atlet Team Singapore.",
        pdpc: "Akta Perlindungan Data Peribadi (PDPA) & Pendaftaran DNC.",
        cnb: "Biro Narkotik Pusat, pemulihan dadah, dan pendidikan pencegahan.",
        sps: "Tempahan lawatan penjara dan Projek Riben Kuning.",
        tadm: "Pengurusan Pertikaian Perburuhan (TADM) & tuntutan gaji.",
        tafep: "Perikatan bagi Amalan Pengambilan Pekerja Adil (TAFEP)."
    },
    ta: {
        ica: "குடியுரிமை நிலை, பாஸ்போர்ட் புதுப்பித்தல் மற்றும் MyICA நியமனங்கள்.",
        eld: "வாக்காளர் பதிவு நிலை மற்றும் வாக்காளர் பட்டியலைச் சரிபார்க்கவும்.",
        iras: "தனிப்பட்ட வருமான வரி தாக்கல், சொத்து வரி மற்றும் GST பதிவுகள்.",
        cpf: "ஓய்வூதிய சேமிப்பு, MediSave கணக்கு மற்றும் முதலாளி caruman.",
        redeemsg: "குடும்ப CDC வவுச்சர்கள் மற்றும் காலநிலை தள்ளுபடிகளைப் பெறுங்கள்.",
        govbenefits: "உறுதிமொழி தொகுப்பு, GST வவுச்சர் மற்றும் NS ரொக்கப் பணத்தைப் பெறுங்கள்.",
        spgroup: "மின்சாரம், நீர், எரிவாயு கணக்குகளைத் திறந்து தள்ளுபடியைச் சரிபார்க்கவும்.",
        skillsfuture: "S$500 திறன்கள் கிரெடிட் மற்றும் பயிற்சிகளை அணுகவும்.",
        wsg: "சிங்கப்பூர் வேலைகளைத் தேடுங்கள், தொழில் மாற்றத் திட்டங்கள் (PCP).",
        mom: "வேலை அனுமதி, வேலைவாய்ப்பு விதிகள் மற்றும் பணி பாஸ் சேவைகள்.",
        moh: "HealthHub செயலி, NEHR மருத்துவப் பதிவுகள் மற்றும் பாலிக்ளினிக் மானியங்கள்.",
        hdb: "BTO பிளாட் விண்ணப்பங்கள், வீட்டு மானியங்கள் மற்றும் கடன் வரம்புகள்.",
        moe: "தொடக்க/உயர்நிலை பள்ளி பதிவு, கட்டணம் மற்றும் உதவித்தொகை.",
        lta: "OneMotoring கணக்கு, COE ஏலம், சாலை வரி மற்றும் போக்குவரத்து வரைபடங்கள்.",
        nea: "காலநிலை வவுச்சர்கள், PSI காற்று தரம் மற்றும் உணவு சுகாதார சோதனைகள்.",
        govsg: "அரசாங்கக் கொள்கை அறிவிப்புகள், பட்ஜெட் மற்றும் செய்திகள்.",
        sgjourney: "புதிய குடிமக்களுக்கான சிங்கப்பூர் பயணம் ஆன்லைன் பயிற்சிகள்.",
        onemap: "சிங்கப்பூர் வரைபடம், பள்ளி தூரம் மற்றும் தொகுதி எல்லைகள்.",
        healthhub: "மருத்துவ சந்திப்புகள், நோயாளி பதிவுகள் மற்றும் பரிசோதனை முடிவுகள்.",
        activesg: "ஜிம், நீச்சல் குளம், விளையாட்டு மைதான முன்பதிவு & இலவச கிரெடிட்கள்.",
        hpb: "Healthy 365 படிகள் சவால், வெகுமதிகள் மற்றும் சுகாதார பரிசோதனை.",
        msf: "ComCare உதவி, குழந்தை போனஸ் மற்றும் குழந்தை பராமரிப்பு மானியங்கள்.",
        pub: "நீர் கட்டணம், வெள்ள எச்சரிக்கை மற்றும் நீர் சேமிப்பு தள்ளுபடி.",
        nlb: "நூலக புத்தகங்கள், மின் புத்தகங்கள் மற்றும் படிப்பு அறை முன்பதிவு.",
        ura: "நகர்ப்புற வளர்ச்சி திட்டம் மற்றும் பொது பார்க்கிங் மண்டலங்கள்.",
        nparks: "பார்பிக்யூ, முகாம் அனுமதி மற்றும் தேசிய பூங்காக்கள் முன்பதிவு.",
        mas: "சிங்கப்பூர் சேமிப்பு பத்திரங்கள் (SSB), கருவூல பில்கள் (T-bill).",
        imda: "SMS அனுப்பியவர் ID பதிவு மற்றும் தொலைத்தொடர்பு புகார்கள்.",
        ns: "தேசிய சேவை (NS) நிலை, வெளியேறும் அனுமதி மற்றும் பதிவு.",
        spf: "சான்றிதழ், போக்குவரத்து அபராதம் மற்றும் மோசடி அறிக்கைகள்.",
        scdf: "தீ பாதுகாப்பு சான்றிதழ், ஆம்புலன்ஸ் மற்றும் myResponder செயலி.",
        acra: "நிறுவன பதிவு, BizFile ஆண்டு அறிக்கைகள் மற்றும் முகவரி மாற்றம்.",
        enterprisesg: "சிறு வணிக மானியங்கள், PSG மற்றும் EDG வளர்ச்சி உதவி.",
        ipos: "வர்த்தக முத்திரை, காப்புரிமை மற்றும் அறிவுசார் சொத்து பாதுகாப்பு.",
        sla: "நிலப் பத்திரங்கள், சொத்து உரிமை INLIS சரிபார்ப்பு.",
        cea: "ரியல் எஸ்டேட் முகவர் உரிம சரிபார்ப்பு மற்றும் புகார்கள்.",
        pa: "மக்கள் கழகம் (CC) பயிற்சிகள் மற்றும் PAssion கார்டு.",
        mindef: "பாதுகாப்பு அமைச்சகம், சிங்கப்பூர் ஆயுதப்படை (SAF).",
        seab: "PSLE, O/A லெவல் தேர்வு முடிவுகள் மற்றும் விண்ணப்பங்கள்.",
        judiciary: "சிங்கப்பூர் நீதிமன்றங்கள் மற்றும் சிறு உரிமைகோரல் தீர்ப்பாயம்.",
        mlaw: "விவாகரத்து, உயில், சட்ட உதவி மற்றும் திவாலா நிலை.",
        sgenable: "மாற்றுத்திறனாளி உதவி, உதவி தொழில்நுட்பம் மற்றும் ஆதரவு.",
        mfa: "வெளிநாட்டுப் பயண ஆலோசனைகள் மற்றும் பதிவு (eRegister).",
        sfa: "உணவு பாதுகாப்பு திரும்பப் பெறுதல் மற்றும் இறக்குமதி உரிமம்.",
        gra: "கேசினோ நுழைவுக் கட்டணம் மற்றும் சூதாட்டக் கட்டுப்பாடு.",
        nac: "தெருக்கலை உரிமம் மற்றும் கலை நிகழ்வு மானியங்கள்.",
        mccy: "தொண்டு நன்கொடைகள், தன்னார்வத் தொண்டு மற்றும் இளைஞர் நடவடிக்கைகள்.",
        rom: "திருமணப் பதிவு (ROM/ROMM) மற்றும் திருமண சான்றிதழ்.",
        csa: "ScamShield மோசடி பாதுகாப்பு மற்றும் இணைய பாதுகாப்பு எச்சரிக்கைகள்.",
        aic: "முதியோர் பராமரிப்பு மையங்கள் மற்றும் பராமரிப்பாளர் மானியங்கள்.",
        muis: "ஹலால் சான்றிதழ், ஜகாத் மற்றும் பள்ளிவாசல் நடவடிக்கைகள்.",
        ssg: "திறன்கள் கிரெடிட் மற்றும் WSQ தகுதிச் சான்றிதழ்கள்.",
        sportsg: "தேசிய விளையாட்டு வளர்ச்சி மற்றும் டீம் சிங்கப்பூர் தடகள வீரர்கள்.",
        pdpc: "தனிப்பட்ட தரவு பாதுகாப்பு சட்டம் (PDPA) & DNC பதிவு.",
        cnb: "மத்திய போதைப்பொருள் பணியகம் மற்றும் போதைப்பொருள் தடுப்பு கல்வி.",
        sps: "சிறை வருகை முன்பதிவு மற்றும் மஞ்சள் ரிப்பன் திட்டம்.",
        tadm: "தொழிலாளர் தகராறு மேலாண்மை (TADM) மற்றும் சம்பள கோரிக்கைகள்.",
        tafep: "நியாயமான வேலைவாய்ப்பு நடைமுறைகளுக்கான கூட்டணி (TAFEP)."
    }
};

// The Co-Pilot's default welcome bubble, per language. Stored as HTML (not markdown) because it's
// injected straight into the chat via getWelcomeHTML() below. Keep <strong>/<em> in sync across langs.
const WELCOME_MESSAGES = {
    en: {
        welcome1: "Welcome, Citizen. I am <strong>MerlionOS</strong>, your unified Singapore government assistant.",
        welcome2: "Ask me anything — e.g. <em>\"What are the HDB grant limits?\"</em> or <em>\"How much SkillsFuture credit do I have?\"</em> — and I'll look it up across all relevant agencies."
    },
    zh: {
        welcome1: "欢迎您，公民。我是 <strong>MerlionOS</strong>，您的统一新加坡政府助理。",
        welcome2: "您可以问我任何问题 —— 例如 <em>“HDB 购房津贴限额是多少？”</em> 或 <em>“我还有多少 SkillsFuture 培训补助金？”</em> —— 我会帮您在所有相关机构中查询。"
    },
    ms: {
        welcome1: "Selamat datang, Warganegara. Saya <strong>MerlionOS</strong>, pembantu kecerdasan buatan bersepadu bagi sektor awam Singapura.",
        welcome2: "Tanya saya apa-apa sahaja — cth. <em>\"Apakah had geran perumahan HDB?\"</em> atau <em>\"Berapakah baki kredit SkillsFuture saya?\"</em> — dan saya akan menyemaknya di semua agensi berkaitan."
    },
    ta: {
        welcome1: "வரவேற்கிறோம், குடிமக்களே. நான் <strong>மெர்லியன்ஓஎஸ்</strong> (MerlionOS), சிங்கப்பூர் அரசாங்கத்தின் ஒருங்கிணைந்த AI உதவியாளர்.",
        welcome2: "என்னிடம் ஏதேனும் கேளுங்கள் — எ.கா. <em>\"HDB மானிய வரம்புகள் என்ன?\"</em> அல்லது <em>\"எனது SkillsFuture கிரெடிட் எவ்வளவு?\"</em> — நான் அனைத்து ஏஜென்சிகளிலும் தேடி பதிலளிப்பேன்."
    }
};

// Returns the default (guest) welcome bubble's inner HTML for the given language, falling back to
// English for any language without a translation. Single source of truth used by both the initial
// render / persona reset (persona.js) and the chat reset button (chat.js) so the welcome always
// matches the active language.
window.getWelcomeHTML = function (lang = window.currentLanguage || "en") {
    const w = WELCOME_MESSAGES[lang] || WELCOME_MESSAGES.en;
    return `<p>${w.welcome1}</p>\n            <p>${w.welcome2}</p>`;
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

    // 1b. Translate placeholder attributes
    document.querySelectorAll("[data-translate-placeholder]").forEach(el => {
        const key = el.getAttribute("data-translate-placeholder");
        if (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) {
            el.placeholder = TRANSLATIONS[lang][key];
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

    // 5. Translate agency card descriptions (.card-desc)
    document.querySelectorAll(".service-card").forEach(card => {
        const agency = card.getAttribute("data-agency");
        const descEl = card.querySelector(".card-desc");
        if (agency && descEl) {
            if (!card.hasAttribute("data-original-desc")) {
                card.setAttribute("data-original-desc", descEl.textContent.trim());
            }
            if (lang !== "en" && AGENCY_DESCRIPTIONS[lang] && AGENCY_DESCRIPTIONS[lang][agency]) {
                descEl.textContent = AGENCY_DESCRIPTIONS[lang][agency];
            } else {
                descEl.textContent = card.getAttribute("data-original-desc");
            }
        }
    });

    // 5b. Translate "Go to Portal" card links
    document.querySelectorAll(".card-link").forEach(link => {
        const icon = link.querySelector("i");
        const iconHtml = icon ? icon.outerHTML : '<i class="fa-solid fa-arrow-up-right-from-square"></i>';
        const txt = (TRANSLATIONS[lang] && TRANSLATIONS[lang]["card-link-text"]) || "Go to Portal";
        link.innerHTML = `${txt} ${iconHtml}`;
    });

    // 6. Refresh active persona UI in the selected language
    if (typeof window.applyPersona === "function" && typeof window.getActivePersonaKey === "function") {
        window.applyPersona(window.getActivePersonaKey(), true);
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
