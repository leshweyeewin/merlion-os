# MerlionOS Co-Pilot & Document Copilot Technical Guide

This document details the architecture, multimodal vision capabilities, PII redaction pipeline, persona contextualization, and multi-channel simulation powering **MerlionOS Co-Pilot**.

---

## 1. Executive Summary

The **MerlionOS Co-Pilot** serves as a unified AI assistant for Singapore public sector digital services. Instead of requiring citizens to navigate 93 statutory portals or understand complex agency acronyms (ICA, IRAS, CPF, HDB, LTA), Co-Pilot accepts natural language queries, uploaded statement documents, or sample simulations, retrieving actionable guidance across all relevant government entities.

```
                    ┌──────────────────────────────────────────────┐
                    │            MerlionOS Co-Pilot Drawer         │
                    └──────────────────────┬───────────────────────┘
                                           │
          ┌────────────────────────────────┼────────────────────────────────┐
          ▼                                ▼                                ▼
┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
│ Document Copilot │            │ Persona Context  │            │ Telegram Channel │
│  Multimodal AI   │            │ 5 Life-Stages    │            │    Co-Pilot      │
└─────────┬────────┘            └─────────┬────────┘            └─────────┬────────┘
          │                               │                               │
          ▼                               ▼                               ▼
┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
│ PDF PII Redaction│            │  Intent Routing  │            │ Same run_chat_   │
│  & Vision Stream │            │ & Policy Engine  │            │ loop engine      │
└──────────────────┘            └──────────────────┘            └──────────────────┘
```

---

## 2. Multimodal Document Copilot

### 2.1 Synthetic Mock Statement Generators
To enable users and judges to evaluate multimodal document analysis without uploading confidential NRIC/FIN numbers or actual tax forms, MerlionOS includes 3 built-in synthetic document generators:

1. **IRAS Notice of Assessment (NOA)**: Generates a realistic mock tax assessment statement with assessable income, employment relief, and CPF relief lines.
2. **CPF Statement**: Generates a mock Central Provident Fund account summary showing Ordinary Account (OA), Special Account (SA), and MediSave (MA) balances.
3. **Monthly Payslip**: Generates a synthetic monthly wage statement with basic pay, allowances, and employee/employer CPF deductions.

Each generator dynamically draws an in-memory PNG document using HTML5 Canvas (`generateSimulatedDocument(type)` in [chat.js](file:///d:/Learn/Google/merlion-os/static/js/chat.js)), attaches the resulting image payload to the active upload preview, and submits it to the vision analysis pipeline.

### 2.2 Server-Side PDF Text Extraction & PII Redaction
When users upload actual PDF documents, MerlionOS executes strict privacy guardrails on the server:

- **PDF Text Extraction**: Uses `pypdf` to extract text streams directly.
- **Regex PII Redaction**: Automatically scans and masks sensitive Singapore personal identification patterns before feeding the text to LLMs:
  - **NRIC / FIN**: Masked matching `[STFGM]\d{7}[A-Z]` (e.g., `S1234567A` $\rightarrow$ `[REDACTED_NRIC]`).
  - **Passport Numbers**: Masked matching `[K-Z]\d{7}[A-Z]` (e.g., `K1234567A` $\rightarrow$ `[REDACTED_PASSPORT]`).
  - **Phone Numbers**: Masked matching Singapore 8-digit mobile/landline formats (`[REDACTED_PHONE]`).

---

## 3. Persona-Tailored Co-Pilot Context

MerlionOS supports **5 demo life-stage persona profiles** that customize Co-Pilot guidance, prompt suggestions, and portal recommendations:

| Persona | Life Stage Profile | Co-Pilot Context Tailoring |
| :--- | :--- | :--- |
| **Guest** | Generic / Unauthenticated | Neutral, comprehensive public service guidance across all 93 agencies. |
| **New Citizen** | 32, naturalized, renting in Punggol, tech sector | Focuses on Singapore Journey onboarding, first tax filing, CPF setup, and first BTO eligibility. |
| **Young Family** | 35, newborn baby, HDB owner in Sengkang, healthcare | Highlights Baby Bonus, Child Development Account (CDA), preschool registration, and MediSave delivery reliefs. |
| **Fresh Graduate** | 25, job-seeking, living in Jurong West | Surfaces MySkillsFuture $500 credit, career conversion programmes (PCP), starting wage benchmarks, and first-job CPF allocation. |
| **Retiree** | 67, retired, HDB owner in Toa Payoh | Focuses on CPF LIFE payout plans, MediShield Life, Silver Support cash payouts, and active aging programmes. |

When a persona is active, `getActivePersona()` attaches structured context parameters to backend prompt requests:
```json
{
  "label": "a new Singapore citizen",
  "age": 32,
  "life_stage": "recently naturalised citizen completing the Singapore Journey onboarding",
  "town": "Punggol",
  "sector": "technology"
}
```

---

## 4. Telegram Channel Co-Pilot

Beyond the in-app Web Drawer, the same AI Co-Pilot is exposed over **Telegram** (`tools/telegram_bot.py`) — so a resident can ask government-services questions from the messaging app they already use, no dashboard visit required:

- Any free-form message is answered by the **same `run_chat_loop` engine** the web drawer uses (`_ai_reply` bridges the sync bot handler to the async chat loop, single-turn/stateless).
- Bot commands still work alongside chat: pairing codes link alerts, `/check <message>` runs a scam scan, `/stop` unlinks, `/help` explains. A message containing a link is auto-scanned for scams as a safety reflex.
- Runs by long-polling (local dev, no public URL) or webhook (Render); see [docs/data_sources.md](data_sources.md) for the alerts/Telegram wiring.

> **Why Telegram and not WhatsApp?** An anonymous showcase visitor can open a Telegram bot instantly, whereas WhatsApp's Business Cloud API requires business verification, an approved template, and per-recipient opt-in — infeasible to demo live and inappropriate for a non-official to send government-styled messages. A WhatsApp simulator previously stood in for this; it was removed in favour of the real, try-it-now Telegram channel.

---

## 5. Verification & Unit Tests

The Co-Pilot suite is validated by these dedicated test suites:
- `tests/test_chat_models.py`: Validates chat request building and model responses.
- `tests/test_document_copilot.py`: Validates document simulation and vision analysis payloads.
- `tests/test_pdf_redaction.py`: Validates regex NRIC/FIN and PII redaction.
- `tests/test_telegram_bot.py`: Validates bot command routing, AI Co-Pilot answering, scam auto-scan, and the webhook.
