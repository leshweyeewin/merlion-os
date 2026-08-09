# MerlionOS Watchlists, Triggered Alerts & ScamShield Security Engine

This document details the architecture, background event pipelines, multi-channel fan-out, and anti-phishing security algorithms powering **MerlionOS Proactive Alerts & Community ScamShield Checker**.

---

## 1. Executive Summary

Civic web applications often suffer from low user retention because citizens only visit during annual tax filing or flat application cycles. 

MerlionOS turns one-time visits into an ongoing habit through two critical engines:
1. **Proactive Watchlists & Triggered Alerts**: Allowing citizens to set custom event triggers (COE drops, BTO launches, town resale price shifts, tax deadlines, MRT disruptions) delivered straight to Telegram, WhatsApp, or Web Push notifications.
2. **Community ScamShield Checker**: Ingesting official `@scamshieldalert` advisories and providing heuristic analysis of suspicious SMS messages or URLs to protect Singaporeans from impersonation scams.

---

## 2. Proactive Watchlists & Triggered Alert Pipeline

### 2.1 Event Pipeline Architecture
The alert engine (`tools/alerts.py`) operates a zero-account, browser-persistent threshold pipeline:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Citizen Preference Watchlist                          │
│        (COE Threshold, BTO Town, Resale Town, Tax Deadline, MRT Line)       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      In-App Evaluator (Cached Signal Data)                  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│  In-App Alert Feed   │   │ Browser Web Push API │   │ Telegram Bot Webhook │
│  (Persistent Badge)  │   │  (Service Worker)    │   │  (@MerlionOS_Bot)    │
└──────────────────────┘   └──────────────────────┘   └──────────────────────┘
```

### 2.2 Threshold Signals & Triggers

| Watchlist Signal | Monitoring Source | Trigger Condition | Notification Payload Example |
| :--- | :--- | :--- | :--- |
| **COE Cat A / Cat B Drop** | LTA DataMall API | Cat A premium drops below target threshold (e.g. `< S$85,000`). | *"🚗 COE Alert: Cat A premium dropped to $84,200 (Target: $85,000). Bidding ends in 24h."* |
| **BTO Launch Announcement** | HDB Press Releases | New BTO exercise launched in chosen town (e.g. *Punggol* or *Tampines*). | *"🏠 BTO Launch Alert: HDB has announced 1,200 BTO units in Punggol for the upcoming launch."* |
| **HDB Resale Median Shift** | BigQuery / data.gov.sg | Median resale price in user's town moves by `> 3%`. | *"📊 Housing Alert: Punggol 4-Room median resale price shifted to $620,000 (+3.2%)."* |
| **IRAS Tax Deadline Warning** | IRAS Calendar Engine | Tax filing deadline is 14 days out. | *"⚖️ Tax Alert: IRAS Income Tax filing deadline is in 14 days (15 April). File via myTax Portal."* |
| **MRT Line Disruption** | LTA DataMall Transit API | MRT line delay or breakdown reported on user's commuting line. | *"🚇 Transit Alert: 15-min delay reported on North-South Line between Bishan and Yishun."* |

---

## 3. Community ScamShield Security Checker

### 3.1 Heuristic Risk Analysis Engine (`tools/scam_checker.py`)
Singapore citizens are frequently targeted by SMS phishing scams impersonating IRAS, CPF, Singpass, or major banks (DBS, OCBC, UOB). The MerlionOS ScamShield Checker evaluates suspicious messages and URLs through 5 deterministic security layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Suspicious SMS Message or URL Input                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          ▼                            ▼                            ▼
┌───────────────────┐        ┌───────────────────┐        ┌───────────────────┐
│ Layer 1: Trusted  │        │ Layer 2: Imperson-│        │ Layer 3: Punycode │
│ Domain Allowlist  │        │  ation & OTP Ask  │        │ & Lookalike Check │
│   (*.gov.sg)      │        │ Detection (Regex) │        │  (Unicode/Hex)    │
└───────────────────┘        └───────────────────┘        └───────────────────┘
          │                            │                            │
          └────────────────────────────┼────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 4 & 5: ScamShield Feed Cross-Reference & Risk Verdict (HIGH/MED/LOW) │
└─────────────────────────────────────────────────────────────────────────────┘
```

1. **Layer 1: Trusted Domain Allowlist (`*.gov.sg`)**: Checks if links belong to verified official domains (`gov.sg`, `ica.gov.sg`, `iras.gov.sg`, `cpf.gov.sg`, `dbs.com.sg`). Official links are flagged as **SAFE**.
2. **Layer 2: Government/Bank Impersonation Detection**: Detects messages claiming to be from "IRAS", "CPF Board", "Singpass", or "DBS" while linking to unverified third-party domains.
3. **Layer 3: Punycode & Character Spoofing Check**: Detects lookalike Cyrillic or Punycode domains (e.g. `iras-gov-sg.xyz` or `dbs-verify.info`).
4. **Layer 4: OTP / Credential Pressure Tactics**: Scans for high-risk phishing keywords (*"account suspended"*, *"click immediately"*, *"enter Singpass OTP"*, *"claim cash payout now"*).
5. **Layer 5: `@scamshieldalert` Cross-Reference**: Matches URLs and phone numbers against live advisories published by the National Crime Prevention Council (NCPC) and SPF ScamShield feeds.

### 3.2 Cross-Channel Availability
The ScamShield Checker is accessible across 3 touchpoints:
- **Web App Dashboard**: Dedicated input box on SG Hub (`#scam-checker-input`).
- **Telegram Bot (`@MerlionOS_Bot`)**: Users can forward suspicious SMS messages directly to the bot for an instant safety verdict.
- **WhatsApp Channel Simulator**: Users can paste links to receive an automated verification response.
