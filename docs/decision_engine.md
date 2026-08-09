# MerlionOS Civic Decision Engine & Life-Event Orchestration

This document details the architecture, policy data models, life-event milestone workflows, and forward-looking foresight tools powering the **MerlionOS Civic Decision Engine**.

---

## 1. Executive Summary

Traditional government portals act as passive display boards—displaying static statutory information and leaving the burden on citizens to manually check eligibility across multiple agencies. 

The **MerlionOS Civic Decision Engine** transforms civic data into personalized decision intelligence through three core capabilities:
1. **Unified "Money Left on the Table" Engine**: Consolidating grants, subsidies, rebates, and tax reliefs into a single headline summary based on 5 basic profile inputs.
2. **End-to-End Life-Event Orchestration**: Assembling multi-agency checklists, deadlines, and grant eligibility across key life milestones (*Having a baby*, *Buying a first flat*, *Career transition*, *Turning 55*, *Starting a business*, *Bereavement*).
3. **Forward-Looking "Should I" Foresight Tools**: Decision calculators combining historical market data, loan rules, and policy thresholds to answer complex citizen questions (*"Can I afford this BTO flat?"*, *"Should I top up CPF SA or SRS?"*, *"When is the optimal COE bidding window?"*).

---

## 2. Unified "Money Left on the Table" Engine

### 2.1 Profile Input Parameters
Instead of filling out multiple lengthy forms across HDB, IRAS, CPF, MSF, and SSG, the Benefits Finder accepts 5 lightweight profile inputs:
- **Citizenship Status**: Citizen, Permanent Resident, Resident Foreign Worker
- **Age / Life Stage**: 18 to 100
- **Monthly Income**: Individual and household gross income
- **Housing Type & Annual Value (AV)**: HDB flat type (1-room to 5-room/Executive) or Private Property AV band
- **Family / Dependent Status**: Single, Married, Number of children, Elderly dependents

### 2.2 Aggregated Benefit Schemes
The engine evaluates eligibility deterministically across national benefit frameworks:

```
                                 ┌──────────────────────────────┐
                                 │    5 Basic Profile Inputs    │
                                 └──────────────┬───────────────┘
                                                │
                                                ▼
                        ┌──────────────────────────────────────────────┐
                        │ Unified "Money Left on the Table" Estimator   │
                        └──────────────────────┬───────────────────────┘
                                               │
   ┌───────────────────┬───────────────────────┼───────────────────────┬───────────────────┐
   ▼                   ▼                       ▼                       ▼                   ▼
┌───────────────┐ ┌───────────────┐   ┌─────────────────┐     ┌───────────────────┐ ┌───────────────┐
│  GovBenefits  │ │ CDC Vouchers  │   ┌─────────────────┐     │    SkillsFuture   │ │  IRAS Reliefs │
│ (AP / GSTV /  │ │  & Climate    │   │  Workfare Income│     │ (S$500 Credit +   │ │ (SRS / RSTU / │
│  NS Payouts)  │ │   Rebates     │   │ Supplement (WIS)│     │ Mid-Career Subsidy│ │ Statutory Caps│
└───────────────┘ └───────────────┘   └─────────────────┘     └───────────────────┘ └───────────────┘
```

- **GovBenefits (MOF)**: Assurance Package (AP) cash payouts, GST Voucher (Cash + U-Save), NS cash credits, Senior Bonus.
- **RedeemSG / CDC Vouchers**: Household CDC vouchers and Climate Vouchers rebates.
- **Workfare Income Supplement (WIS)**: Payouts for lower-income Singaporean workers aged 30+.
- **SkillsFuture (SSG)**: S$500 opening credit + S$4,000 Mid-Career SkillsFuture top-up for citizens aged 40+.
- **Enhanced CPF Housing Grant (EHG)**: Up to S$80,000 housing grant for first-time home buyers based on household income.
- **IRAS Tax Relief Optimizer**: Unclaimed pre-existing tax reliefs, CPF SA (RSTU) top-ups, and Supplementary Retirement Scheme (SRS) relief up to the S$80,000 statutory relief cap.

The output displays a single sticky summary banner:  
> *"Based on your profile, you may be eligible for **~$14,250** across Baby Bonus, CDC/GST Vouchers, Workfare, SkillsFuture, and EHG, plus **~$7,000** in unclaimed tax reliefs."*

---

## 3. End-to-End Life-Event Orchestration

MerlionOS orchestrates multi-agency actions across major citizen life milestones:

| Life Milestone | Participating Agencies | Integrated Actions & Workflow |
| :--- | :--- | :--- |
| 👶 **Having a Baby** | MSF, MOH, CPF, GovTech, ICA | Baby Bonus Scheme cash gift, Child Development Account (CDA) matching, MediSave maternity claim limits, birth registration, and MediShield Life auto-coverage. |
| 🏠 **Buying First Flat** | HDB, CPF, IRAS, SLA, URA | BTO launch tracking, HDB Flat Eligibility (HFE) letter application, EHG grant estimation, CPF Ordinary Account (OA) withdrawal, Stamp Duty (BSD/ABSD) calculation, and home loan limits (MSR/TDSR). |
| 💼 **Career Transition** | WSG, SSG, MOM, NTUC | Career Conversion Programmes (CCP/PCP), SkillsFuture mid-career course subsidies, Workfare training support, and unemployment/retrenchment guidance. |
| 👵 **Turning 55 / Retirement** | CPF, MOH, IRAS, AIC | CPF Retirement Account (RA) creation, Basic/Full Retirement Sum (BRS/FRS) calculation, CPF LIFE payout estimations (Standard vs Basic vs Escalating), and MediShield Life / CareShield Life coverage. |
| 🏬 **Starting a Business** | ACRA, EnterpriseSG, IRAS, MOM | BizFile+ business registration, SME PSG/EDG grant eligibility, corporate tax incentives, and foreign worker levy rules. |
| 🕊️ **Bereavement** | NEA, CPF, MSF, Police, ICA | Death registration guidance, CPF nomination payout procedures, funeral arrangement permits, and estate probate/administration links. |

---

## 4. Forward-Looking "Should I" Decision Foresight Tools

### 4.1 HDB Home Affordability Calculator (`tools/housing.py`)
Combines live median resale prices across 26 HDB towns, EHG housing grant caps, Mortgage Servicing Ratio (MSR = 30%), and Total Debt Servicing Ratio (TDSR = 55%) to answer:  
> *"Can I afford a 4-room resale flat in Punggol on a S$6,500 household income?"*

### 4.2 IRAS Tax Relief & SRS Optimizer (`tools/iras_optimizer.py`)
Calculates the marginal tax savings of topping up CPF Special Account (RSTU) vs. Supplementary Retirement Scheme (SRS), taking into account existing CPF employee contributions, Earned Income Relief, NSman Relief, Parent Relief, and enforcing the **S$80,000 statutory tax relief cap**.

### 4.3 CPF LIFE Retirement Estimator (`tools/cpf_life.py`)
Simulates projected monthly payouts under **CPF LIFE** starting at age 65 under three statutory plans:
- **Standard Plan**: Higher monthly payouts, lower bequest.
- **Basic Plan**: Lower monthly payouts, higher bequest.
- **Escalating Plan**: Payouts start lower and increase by 2% annually to counter inflation.

### 4.4 COE Bidding Timing & Price Forecast (`tools/transport.py`)
Applies linear-regression models on LTA DataMall historical quota allocations and bidding demand trends to forecast Cat A and Cat B premiums for the upcoming bidding exercise, giving vehicle buyers timing foresight.
