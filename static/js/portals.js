// portals.js — SG Portals directory: intent search, drag reorder, show/hide, onboarding
// banner, and My Matters bookmarks (all persisted in localStorage).

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

    // The quick-task chips inside #quick-task-chips are rendered per-persona by persona.js
    // (renderPersonaQuickTasks); the input/clear handlers below still manage their active state
    // via a live querySelectorAll, so they work regardless of which persona rendered them.
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

    window.applyPortalSearch = applySearch;
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

    const sortAzBtn = document.getElementById("sort-alphabetical-btn");
    if (sortAzBtn) {
        let sortAsc = false; // false so first click toggles to true (A→Z)
        sortAzBtn.addEventListener("click", () => {
            sortAsc = !sortAsc;
            const icon = document.getElementById("sort-icon");
            if (icon) {
                icon.className = sortAsc
                    ? "fa-solid fa-arrow-down-a-z"
                    : "fa-solid fa-arrow-down-z-a";
            }
            const cards = Array.from(grid.querySelectorAll(".service-card"));
            cards.sort((a, b) => {
                const nameA = (a.querySelector("h3")?.textContent || a.dataset.agency).trim();
                const nameB = (b.querySelector("h3")?.textContent || b.dataset.agency).trim();
                return sortAsc
                    ? nameA.localeCompare(nameB)
                    : nameB.localeCompare(nameA);
            });
            cards.forEach(card => grid.appendChild(card));
            saveOrder();
            window.dispatchEvent(new CustomEvent("portals-reordered"));
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            localStorage.removeItem(STORAGE_KEY);
            applyOrder(defaultOrder);
            window.dispatchEvent(new CustomEvent("portals-reordered"));
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
                <div class="hidden-portals-empty" style="margin: 12px 0;">No matching portals.</div>`;
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
                ${panelMode === 'hidden' ? `
                    <button type="button" class="mp-bulk-btn mp-add" id="mp-bulk-add" style="width: 100%;">Add back selected</button>
                ` : `
                    <button type="button" class="mp-bulk-btn mp-hide" id="mp-bulk-hide" style="width: 100%;">Hide selected</button>
                `}
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
        btn.addEventListener("mousedown", (e) => e.stopPropagation());
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
        const showAllGlobalBtn = document.getElementById("mp-show-all-global");
        if (showAllGlobalBtn) {
            showAllGlobalBtn.addEventListener("click", () => {
                const list = allCards().map(c => c.dataset.agency);
                bulkApply(list, showPortal);
            });
        }
        const hideAllGlobalBtn = document.getElementById("mp-hide-all-global");
        if (hideAllGlobalBtn) {
            hideAllGlobalBtn.addEventListener("click", () => {
                const list = allCards().map(c => c.dataset.agency);
                bulkApply(list, hidePortal);
            });
        }

        manageBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const willOpen = dropdown.classList.contains("hidden");
            if (willOpen) {
                selected.clear();
                renderDropdown();
                // Position is CSS-driven: absolute below the button on desktop, and a fixed
                // bottom-anchored sheet on mobile (always fully on-screen, independent of how far
                // the toolbar button has scrolled). Clear any stale inline top from older logic
                // that anchored the mobile panel to the button and dropped it off the fold.
                dropdown.style.top = "";
            }
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
            e.stopPropagation();
            const modeBtn = e.target.closest(".mp-mode-btn");
            if (modeBtn) {
                panelMode = modeBtn.dataset.mode;
                selected.clear();
                renderDropdown();
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

        window.addEventListener("portals-reordered", () => {
            if (dropdown && !dropdown.classList.contains("hidden")) {
                renderDropdown();
            }
        });
    }
}

function initOnboardingBanner() {
    const banner = document.getElementById("onboarding-banner");
    const dismissBtn = document.getElementById("onboarding-dismiss");
    if (!banner || !dismissBtn) return;

    const dismissed = localStorage.getItem("merlionos-onboarding-dismissed");
    if (!dismissed) {
        banner.style.display = "block";
    }

    dismissBtn.addEventListener("click", () => {
        banner.style.display = "none";
        localStorage.setItem("merlionos-onboarding-dismissed", "true");
    });
}

function initPortalBookmarks() {
    const grid = document.querySelector(".grid-container");
    const mattersSection = document.getElementById("my-matters-section");
    const mattersGrid = document.getElementById("my-matters-grid");
    const clearBtn = document.getElementById("my-matters-clear");
    if (!grid || !mattersSection || !mattersGrid) return;

    const STORAGE_KEY = "merlionos-bookmarked-portals";

    function loadBookmarks() {
        try {
            const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
            return Array.isArray(saved) ? saved : [];
        } catch (e) {
            return [];
        }
    }

    function saveBookmarks(list) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    }

    function toggleBookmark(agency) {
        let list = loadBookmarks();
        if (list.includes(agency)) {
            list = list.filter(a => a !== agency);
        } else {
            list.push(agency);
        }
        saveBookmarks(list);
        updateCardStars();
        renderMattersGrid();
    }

    function updateCardStars() {
        const bookmarks = new Set(loadBookmarks());
        grid.querySelectorAll(".service-card").forEach(card => {
            const agency = card.dataset.agency;
            const star = card.querySelector(".bookmark-btn");
            if (star) {
                if (bookmarks.has(agency)) {
                    star.classList.add("bookmarked");
                    star.title = "Remove from bookmarks";
                } else {
                    star.classList.remove("bookmarked");
                    star.title = "Bookmark this portal";
                }
            }
        });
    }

    function renderMattersGrid() {
        mattersGrid.innerHTML = "";
        const bookmarks = loadBookmarks();

        // My Matters stays visible even when empty, so the ★ feature is discoverable
        // (otherwise users never learn the star exists — chicken-and-egg). Show a
        // friendly empty-state card until the first portal is pinned.
        mattersSection.classList.remove("hidden");

        // "Clear all" only makes sense once something is pinned
        if (clearBtn) clearBtn.classList.toggle("hidden", bookmarks.length === 0);

        if (bookmarks.length === 0) {
            const empty = document.createElement("div");
            empty.className = "my-matters-empty";
            empty.innerHTML = `⭐ No pinned portals yet — click the <i class="fa-solid fa-star"></i> star icon on any portal card below to pin your frequent portals here for 1-click access!`;
            mattersGrid.appendChild(empty);
            return;
        }

        bookmarks.forEach(agency => {
            const origCard = grid.querySelector(`.service-card[data-agency="${agency}"]`);
            if (!origCard) return;

            const clone = origCard.cloneNode(true);
            clone.removeAttribute("draggable");
            clone.querySelectorAll(".drag-handle").forEach(el => el.remove());
            clone.querySelectorAll(".hide-portal-btn").forEach(el => el.remove());
            
            // Hook up clone star button
            const cloneStar = clone.querySelector(".bookmark-btn");
            if (cloneStar) {
                cloneStar.addEventListener("click", (e) => {
                    e.stopPropagation();
                    toggleBookmark(agency);
                });
            }

            mattersGrid.appendChild(clone);
        });
    }

    // Add star buttons to all original cards
    grid.querySelectorAll(".service-card").forEach(card => {
        const agency = card.dataset.agency;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "bookmark-btn";
        btn.innerHTML = `<i class="fa-solid fa-star"></i>`;
        btn.addEventListener("mousedown", (e) => e.stopPropagation());
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleBookmark(agency);
        });
        card.appendChild(btn);
    });

    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            if (!loadBookmarks().length) return;
            saveBookmarks([]);
            updateCardStars();
            renderMattersGrid();
        });
    }

    updateCardStars();
    renderMattersGrid();
}

