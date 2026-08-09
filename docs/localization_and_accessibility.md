# MerlionOS Localization, Intent Search & Accessibility Architecture

This document details the **4-Language National Localization Architecture**, **Singov Official Terminology Alignment**, **Plain English Intent-Based Search Engine**, **Life-Stage Personas**, and **Elderly Accessibility Mode** implemented in MerlionOS.

---

## 1. Executive Summary

Singapore is an officially quadrilingual nation with four official languages: **English**, **Chinese (中文)**, **Malay (Bahasa Melayu)**, and **Tamil (தமிழ்)**. MerlionOS provides 1-click language switching across the entire platform, standardizing statutory agency names, benefit schemes, portal action links, and quick tasks against official Singapore Government Glossaries.

In addition, MerlionOS addresses civic digital inclusion through an **Elderly / Accessibility Mode** (enlarged typography, high-contrast UI) and a **Plain-English Intent Search Engine** that bridges the gap between everyday citizen phrases (*"renew passport"*) and official statutory board names (*Immigration & Checkpoints Authority*).

---

## 2. 4-Language National Localization Architecture

### 2.1 Supported Languages & Switching Engine
Localization is managed by `static/js/translations.js` via a centralized dictionary `TRANSLATIONS` and dynamic DOM attribute binding (`data-translate` and `data-translate-placeholder`):

- **Languages Supported**:
  - `en`: English (Default)
  - `zh`: Chinese (中文)
  - `ms`: Malay (Bahasa Melayu)
  - `ta`: Tamil (தமிழ்)
- **Persistence**: User selection is saved to `localStorage` under `merlion_language` and synced across sessions.

### 2.2 Standardized Singov Official Terminology Glossary
To ensure translations sound natural and authentic in the Singapore public sector context, all localized strings adhere strictly to official **Singov Communication Division (GCD)**, **Lianhe Zaobao (联合早报)**, **Berita Harian**, and **Tamil Murasu** statutory term glossaries:

| Scheme / Concept | English Standard | Chinese (中文) Official Term | Malay (Melayu) Official Term | Tamil (தமிழ்) Official Term |
| :--- | :--- | :--- | :--- | :--- |
| **BTO Flat** | Build-To-Order Flat | **预购组屋 (BTO)** *(Not 期房/预售屋)* | Flat BTO | BTO பிளாட் |
| **Resale Flat** | Resale HDB Flat | **转售组屋** | Flat Resale | மறுவிற்பனை பிளாட் |
| **CPF Board** | Central Provident Fund | **中央公积金 (CPF)** | Lembaga CPF | மத்திய சேம நிதி (CPF) |
| **CDC Vouchers** | CDC Household Vouchers | **社理会消费券 (CDC Vouchers)** | Baucar CDC | CDC வவுச்சர்கள் |
| **Climate Vouchers** | Climate Vouchers | **绿色环保券 (Climate Vouchers)** | Baucar Iklim | காலநிலை வவுச்சர்கள் |
| **Notice of Assessment** | IRAS NOA Tax Bill | **缴税通知单 (NOA)** | Notice of Assessment | Notice of Assessment |
| **MediShield Life** | MediShield Life | **终身健保 (MediShield Life)** | MediShield Life | MediShield Life |
| **Pioneer Generation** | Pioneer Generation | **建国一代 (Pioneer Generation)** | Generasi Perintis | முன்னோடி தலைமுறை |
| **SkillsFuture Credit** | MySkillsFuture Credit | **技能创前程培训补助** | Kredit SkillsFuture | SkillsFuture கிரெடிட் |
| **Assurance Package** | Assurance Package | **定心与支援套餐** | Pakej Jaminan | உறுதிமொழி தொகுப்பு |

### 2.3 Dynamic Card Description & Link Translation
All 93 statutory agency cards in the main directory (`.service-card`) dynamically localize their description text (`AGENCY_DESCRIPTIONS`) and action link text (`card-link-text`) when switching languages:

- **English**: `Go to Portal` $\rightarrow$ `Citizenship status, passport renewal, and MyICA appointments.`
- **Chinese**: `前往门户` $\rightarrow$ `公民身份、护照更新及 MyICA 预约服务。`
- **Malay**: `Ke Portal` $\rightarrow$ `Status kewarganegaraan, pembaruan pasport, dan janji temu MyICA.`
- **Tamil**: `போர்ட்டலுக்குச் செல்` $\rightarrow$ `குடியுரிமை நிலை, பாஸ்போர்ட் புதுப்பித்தல் மற்றும் MyICA நியமனங்கள்.`

---

## 3. Plain English Intent-Based Search Engine

Citizens often do not know official government jargon or statutory agency names (e.g. searching *"open a shophouse company"* instead of *Accounting and Corporate Regulatory Authority (ACRA)*).

MerlionOS implements an **Intent-Based Search Index** in `static/js/portals.js`:

- **Everyday Synonym Index (`PORTAL_INTENTS`)**: Maps everyday phrases to agency IDs:
  - `ica`: *"renew passport", "apply passport", "nric", "citizenship", "pr", "visa"*
  - `iras`: *"income tax", "property tax", "stamp duty", "tax relief", "noa"*
  - `hdb`: *"buy flat", "apply bto", "resale", "housing loan", "hle", "season parking"*
  - `acra`: *"register company", "business registration", "bizfile", "change company address"*
  - `lta`: *"road tax", "coe", "vehicle car", "driving licence", "onemotoring"*
- **Unified Search Matching**: Matches user search input simultaneously across agency acronyms (`h3`), agency full names (`p`), card descriptions (`.card-desc`), and the `PORTAL_INTENTS` synonym index.
- **Cross-Tab Live Suggestions**: If a user searches for *"coe car price"*, the search engine automatically surfaces a highlighted suggestion box pointing to the live COE dashboard in **SG Hub**.

---

## 4. Demo Life-Stage Personas

To demonstrate how MerlionOS tailors guidance across different citizen demographics without exposing real identity data, MerlionOS includes **5 built-in life-stage profiles** (`static/js/persona.js`):

1. **Guest**: Generic browsing profile for unauthenticated visitors.
2. **New Citizen**: 32, naturalized, renting in Punggol, tech sector — tailors prompt chips to Singapore Journey, first tax filing, and BTO rules.
3. **Young Family**: 35, newborn baby, HDB owner in Sengkang — tailors prompt chips to Baby Bonus, childcare grants, and primary school registration.
4. **Fresh Graduate**: 25, job-seeking, living in Jurong West — tailors prompt chips to SkillsFuture credits, starting wage benchmarks, and first-job CPF allocation.
5. **Retiree**: 67, retired, HDB owner in Toa Payoh — tailors prompt chips to CPF LIFE payouts, MediShield Life, and Silver Support cash payouts.

Selecting a persona instantly translates the persona banner, dropdown lists, bio summaries, and quick task chips into the active UI language.

---

## 5. Elderly & Accessibility Mode

To ensure senior citizens and visually impaired users can easily navigate government services, MerlionOS features a **1-click Elderly Accessibility Mode**:

- **Toggle Switch**: Accessible from the main dashboard header (`#elderly-mode-toggle-hdr`).
- **CSS Class Binding**: Toggles `.elderly-mode` on `document.body`.
- **Styling Adaptations**:
  - Scales base font sizes from 13.5px to **16px–18px**.
  - Increases button hit target padding for easier touch/click navigation.
  - Boosts text contrast and border contrast ratios for improved readability.
  - Expands line-height to 1.6 for comfortable reading.
- **Persistence**: Saved in `localStorage` under `merlion_elderly_mode` so preference persists across page reloads.
