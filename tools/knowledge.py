"""
tools/knowledge.py — Retrieval-Augmented Generation (RAG) knowledge base
--------------------------------------------------------------------------
A small, curated corpus of authoritative Singapore civic facts that the Co-Pilot can retrieve
from for open-ended policy/eligibility questions the 14 agency tools don't specifically cover.

Design: RAG-as-a-tool. `search_knowledge_base` is registered in tools/chat.py's TOOL_MAP, so the
existing multi-hop agent loop calls it like any other tool — no separate vector-DB service. Each
chunk carries a source URL so the model can cite official pages, keeping answers grounded instead
of relying on parametric memory (the "no RAG / citation risk" gap flagged in review).

Embeddings use Gemini `gemini-embedding-001` (768-dim, retrieval task types) via the same SDK the
chat loop uses, and are cached to .data_cache/ keyed by a corpus fingerprint so we only re-embed
when the corpus text actually changes. Cosine similarity is pure-Python (no numpy dependency) —
the corpus is tiny, so per-query ranking cost is negligible.

Content is grounded in MerlionOS's own vetted civic-tool responses plus stable, well-known
official facts; where an exact current figure would be needed, chunks point to the official page
rather than asserting a number that could drift.
"""

import os
import json
import math
import hashlib
import logging

from tools.core import _DISK_CACHE_DIR

logger = logging.getLogger("merlion-os-knowledge")

_EMBED_MODEL = "gemini-embedding-001"
_EMBED_DIM = 768
_CACHE_PATH = os.path.join(_DISK_CACHE_DIR, "kb_embeddings.json")

# ── Curated corpus ────────────────────────────────────────────────────────────
# Each entry: id, title, agency, source_url, text. Keep `text` self-contained (2–4 sentences)
# so a retrieved chunk reads well on its own. Prefer stable facts + official source pointers over
# precise figures that change year to year.
KNOWLEDGE_BASE = [
    # ── Citizenship & identity (ICA) ──
    {"id": "ica-citizenship", "title": "Singapore citizenship application", "agency": "ICA",
     "source_url": "https://www.ica.gov.sg/",
     "text": "Singapore citizenship is applied for through the ICA MyICA portal. Standard applications take roughly 12 months to process. Applicants approved via an In-Principle Approval (IPA) must complete onboarding steps within the stated window before their citizenship is confirmed."},
    {"id": "ica-passport", "title": "Passport renewal", "agency": "ICA",
     "source_url": "https://www.ica.gov.sg/",
     "text": "Singapore passports are renewed online via the MyICA portal; most applications do not require an in-person visit. Renew before your travel date as processing takes several working days, and collection or verification appointments (when required) must be pre-booked."},
    {"id": "ica-nric", "title": "NRIC registration and re-registration", "agency": "ICA",
     "source_url": "https://www.ica.gov.sg/",
     "text": "The NRIC (National Registration Identity Card) is issued by ICA. Residents must re-register for a new NRIC at ages 15 and 30, and report a lost or damaged card. New citizens collect their pink NRIC after registration; collection appointments are booked through MyICA."},
    {"id": "sg-journey", "title": "Singapore Citizenship Journey", "agency": "ICA",
     "source_url": "https://www.sgjourney.gov.sg/",
     "text": "New citizens complete the Singapore Citizenship Journey: online e-Journey modules on local history and civic systems, an experiential visit to national landmarks, and a community sharing session with grassroots leaders. These must be completed within the onboarding window before the citizenship ceremony."},

    # ── CPF ──
    {"id": "cpf-overview", "title": "What CPF is and its accounts", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "The Central Provident Fund (CPF) is Singapore's mandatory social-security savings scheme for citizens and PRs. Contributions are split across the Ordinary Account (OA, for housing and approved investments), Special Account (SA, for retirement), and MediSave Account (MA, for healthcare and MediShield Life premiums)."},
    {"id": "cpf-contributions", "title": "CPF contributions for employees", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "For employees, both employer and employee make monthly CPF contributions as a percentage of wages, with rates that vary by age band. Contributions begin once you take up employment as a citizen or PR. Check the CPF website for the current contribution-rate tables by age."},
    {"id": "cpf-medisave", "title": "MediSave", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "MediSave is the CPF account used for personal and family healthcare — hospitalisation, approved outpatient treatments, and MediShield Life premiums. A portion of every CPF contribution flows into MediSave, subject to a Basic Healthcare Sum ceiling."},
    {"id": "cpf-life", "title": "CPF LIFE retirement payouts", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "CPF LIFE is the national annuity scheme that provides monthly payouts for life from your payout eligibility age. The payout amount depends on how much you have set aside in your Retirement Account and the plan you choose. Members can use the CPF payout estimator to plan retirement income."},
    {"id": "cpf-housing", "title": "Using CPF for housing", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "CPF Ordinary Account savings can be used for the down payment and monthly instalments on an HDB flat or private property, subject to withdrawal limits and valuation rules. Using CPF for housing reduces the amount compounding for retirement, so weigh cash versus CPF payment."},
    {"id": "cpf-topup", "title": "CPF top-ups and tax relief", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "Cash top-ups to your own or a loved one's Special/Retirement Account under the Retirement Sum Topping-Up scheme can earn attractive CPF interest and qualify for income-tax relief, subject to annual caps. This is a common year-end tax-planning move for citizens and PRs."},

    # ── Tax (IRAS) ──
    {"id": "iras-who-files", "title": "Who must file income tax", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "Most tax residents who earn above the filing threshold must file an annual income-tax return with IRAS, though many are on the No-Filing Service if their income is auto-included. New taxpayers and those with additional income (rental, side trade) should verify their filing obligation each year."},
    {"id": "iras-deadline", "title": "Income tax filing deadline", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "Individual income tax is filed after the year of assessment opens, typically with an e-filing deadline in mid-April. Employment income is often auto-included via the Auto-Inclusion Scheme. Late filing can attract penalties, so file or confirm your pre-filled return before the deadline."},
    {"id": "iras-reliefs", "title": "Tax reliefs", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "Chargeable income can be reduced by reliefs such as earned income relief, CPF cash top-up relief, SRS contributions, parenthood and child reliefs, and course-fee relief. Total personal income-tax relief is subject to an overall cap. Use the IRAS relief checker to see what you qualify for."},
    {"id": "iras-srs", "title": "Supplementary Retirement Scheme (SRS)", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "The Supplementary Retirement Scheme (SRS) is a voluntary savings scheme: contributions reduce your chargeable income (up to an annual cap that differs for citizens/PRs and foreigners), and only 50% of withdrawals at retirement age are taxable. It complements CPF for higher-income tax planning."},
    {"id": "iras-property-tax", "title": "Property tax", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "Property tax is an annual tax on property ownership, calculated from the Annual Value of the property with progressive rates that are lower for owner-occupied homes. It is separate from income tax and is billed by IRAS, usually payable by end-January."},
    {"id": "iras-gst", "title": "Goods and Services Tax (GST)", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "GST is Singapore's broad-based consumption tax charged on most goods and services. Lower-income households receive support through the GST Voucher scheme to offset the impact. Only GST-registered businesses charge and remit GST."},

    # ── Housing (HDB) ──
    {"id": "hdb-bto-vs-resale", "title": "BTO vs resale flats", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "A Build-To-Order (BTO) flat is bought new directly from HDB through periodic sales launches and typically costs less but involves a waiting period for construction. A resale flat is bought on the open market from an existing owner — available immediately but usually more expensive. Both have eligibility conditions and grant options."},
    {"id": "hdb-eligibility", "title": "HDB flat eligibility schemes", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "Eligibility to buy an HDB flat depends on citizenship, the eligibility scheme (e.g. Public Scheme for families, Fiancé/Fiancée Scheme, Single Singapore Citizen Scheme), age, and income ceilings. At least one buyer must be a Singapore citizen for most new-flat purchases."},
    {"id": "hdb-grants", "title": "CPF housing grants", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "First-time buyers may receive CPF housing grants such as the Enhanced CPF Housing Grant (EHG), which scales with household income, plus additional grants for resale purchases near family. Grants are credited to the CPF Ordinary Account. Use the HDB flat-eligibility and grant calculators to estimate your amount."},
    {"id": "hdb-loan", "title": "HDB loan vs bank loan", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "Flat buyers can take an HDB housing loan (fixed concessionary interest, requires an HDB Flat Eligibility letter) or a bank loan (market interest, can be lower but fluctuates). The loan-to-value limit caps how much you can borrow; the rest is paid via CPF and cash."},
    {"id": "hdb-eip", "title": "Ethnic Integration Policy (EIP)", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "The Ethnic Integration Policy (EIP) and Singapore Permanent Resident quota set limits on the proportion of flats owned by each ethnic group in a block and neighbourhood, to promote integration. A resale transaction can be blocked if the relevant quota is already met, so buyers should check EIP eligibility before committing."},

    # ── Employment (MOM) ──
    {"id": "mom-work-passes", "title": "Work passes", "agency": "MOM",
     "source_url": "https://www.mom.gov.sg/",
     "text": "Foreigners working in Singapore need a valid work pass from the Ministry of Manpower — commonly the Employment Pass (professionals), S Pass (mid-skilled), or Work Permit (semi-skilled). Passes have qualifying salary and eligibility criteria and are applied for by the employer."},
    {"id": "mom-employment-rights", "title": "Employment rights and leave", "agency": "MOM",
     "source_url": "https://www.mom.gov.sg/",
     "text": "The Employment Act sets baseline rights including paid annual leave, sick leave, public holidays, and timely salary payment. Statutory maternity and paternity leave are also provided. Disputes can be raised with MOM or the Tripartite Alliance for Dispute Management."},
    {"id": "mom-retrenchment", "title": "Retrenchment support", "agency": "MOM",
     "source_url": "https://www.mom.gov.sg/",
     "text": "Employers carrying out retrenchments are expected to follow responsible, fair practices and notify MOM. Affected workers can access career-transition help through Workforce Singapore and NTUC's Employment and Employability Institute (e2i), including job matching and reskilling programmes."},

    # ── Benefits & schemes ──
    {"id": "cdc-vouchers", "title": "CDC vouchers", "agency": "RedeemSG / CDC",
     "source_url": "https://vouchers.cdc.gov.sg/",
     "text": "CDC vouchers are given to Singaporean households to spend at participating heartland merchants and supermarkets, claimed via Singpass on the RedeemSG platform. They are part of government support to help with the cost of living; check the official site for the current tranche and expiry."},
    {"id": "climate-vouchers", "title": "Climate vouchers", "agency": "NEA",
     "source_url": "https://www.nea.gov.sg/",
     "text": "Climate Vouchers help HDB households buy energy- and water-efficient appliances and fittings, encouraging greener consumption. They are redeemed at participating retailers; eligibility and voucher value are set by the scheme in force."},
    {"id": "skillsfuture", "title": "SkillsFuture Credit", "agency": "SkillsFuture",
     "source_url": "https://www.myskillsfuture.gov.sg/",
     "text": "SkillsFuture Credit gives Singapore citizens an opening credit to offset approved course fees, topped up periodically. Mid-career Singaporeans aged 40 and above receive additional support for reskilling. Browse and pay for eligible courses through the MySkillsFuture portal."},
    {"id": "comcare", "title": "ComCare financial assistance", "agency": "MSF",
     "source_url": "https://www.msf.gov.sg/",
     "text": "ComCare provides social assistance for low-income individuals and families — short-to-medium-term help, long-term assistance for those unable to work, and support for household emergencies. Applications are made through Social Service Offices; the MSF site lists eligibility."},
    {"id": "baby-bonus", "title": "Baby Bonus", "agency": "MSF",
     "source_url": "https://www.msf.gov.sg/",
     "text": "The Baby Bonus Scheme supports parents with a cash gift and a matched Child Development Account (CDA) that co-funds savings for a child's healthcare and education. Eligibility relates to the child's citizenship and birth order; enrol via the Baby Bonus online portal."},

    # ── Healthcare ──
    {"id": "medishield-life", "title": "MediShield Life", "agency": "MOH",
     "source_url": "https://www.moh.gov.sg/",
     "text": "MediShield Life is a basic health insurance that covers all Singapore citizens and PRs for life, helping pay for large hospital bills and selected costly outpatient treatments. Premiums can be paid from MediSave and rise with age; no one is excluded for pre-existing conditions."},
    {"id": "chas", "title": "CHAS subsidies", "agency": "MOH",
     "source_url": "https://www.moh.gov.sg/",
     "text": "The Community Health Assist Scheme (CHAS) gives citizens subsidies for medical and dental care at participating GP and dental clinics, with higher subsidies for lower-income households and Pioneer/Merdeka Generation seniors. Apply for a CHAS card to use the subsidies."},
    {"id": "healthier-sg", "title": "Healthier SG and polyclinics", "agency": "MOH",
     "source_url": "https://www.moh.gov.sg/",
     "text": "Healthier SG encourages residents to enrol with a regular family doctor for preventive care and health plans. Polyclinics provide subsidised primary care, and HealthHub lets citizens view records, appointments, and screening reminders online."},
    {"id": "healthhub", "title": "HealthHub", "agency": "HealthHub",
     "source_url": "https://www.healthhub.sg/",
     "text": "HealthHub is the national platform to access personal health records (via the National Electronic Health Record), book polyclinic and hospital appointments, view child health booklets, and track health-screening and vaccination history using Singpass."},

    # ── Education (MOE) ──
    {"id": "moe-p1", "title": "Primary 1 registration", "agency": "MOE",
     "source_url": "https://www.moe.gov.sg/",
     "text": "Primary 1 registration runs in phases each year, with priority for siblings of current pupils, children of alumni or staff, and those living near the school. Distance from the school (home-school proximity) is a key tie-breaker, so check the school's catchment before registering."},
    {"id": "moe-fees", "title": "School fees and financial assistance", "agency": "MOE",
     "source_url": "https://www.moe.gov.sg/",
     "text": "Government and government-aided schools charge low or no fees for Singapore citizens at primary level, with modest miscellaneous fees. The MOE Financial Assistance Scheme (FAS) helps lower-income citizen families with fees, textbooks, and transport; apply through the school."},
    {"id": "moe-scholarships", "title": "Scholarships and bursaries", "agency": "MOE",
     "source_url": "https://www.moe.gov.sg/",
     "text": "MOE and other agencies offer scholarships and bursaries at secondary, pre-university, and tertiary levels based on merit and/or financial need. Higher-education students can also tap government bursaries and the CPF Education Loan Scheme to fund studies."},

    # ── Transport (LTA) ──
    {"id": "lta-coe", "title": "Certificate of Entitlement (COE)", "agency": "LTA",
     "source_url": "https://www.lta.gov.sg/",
     "text": "A Certificate of Entitlement (COE) gives the right to own a vehicle in Singapore for 10 years and is won through a competitive bidding exercise held twice a month, with prices (premiums) varying by vehicle category. The COE is a major part of the cost of car ownership."},
    {"id": "lta-road-tax", "title": "Road tax and vehicle costs", "agency": "LTA",
     "source_url": "https://www.lta.gov.sg/",
     "text": "Vehicle owners pay annual road tax (based on engine capacity or power) via OneMotoring, on top of the COE, registration fees, and ARF. Road tax must be renewed and the vehicle insured before it can be legally driven."},
    {"id": "lta-concessions", "title": "Public transport concessions", "agency": "LTA",
     "source_url": "https://www.lta.gov.sg/",
     "text": "Students, senior citizens, and persons with disabilities are eligible for concession travel cards giving cheaper bus and MRT fares. Adult commuters use an EZ-Link or SimplyGo account; fare rebates and workfare transport support exist for lower-income workers."},

    # ── Civic & digital ──
    {"id": "eld-voting", "title": "Voting in Singapore", "agency": "ELD",
     "source_url": "https://www.eld.gov.sg/",
     "text": "Voting is compulsory for Singapore citizens aged 21 and above at general and presidential elections. Check and update your registration on the electoral register via the Elections Department; a voter who fails to vote is removed from the register until they restore their status."},
    {"id": "ns", "title": "National Service (NS)", "agency": "MINDEF / OneNS",
     "source_url": "https://www.ns.gov.sg/",
     "text": "National Service (NS) is a duty for male Singapore citizens and second-generation PRs, comprising full-time service followed by reservist (Operationally Ready National Service) cycles. NSmen manage status, In-Camp Training, and benefits through the OneNS portal."},
    {"id": "singpass-safety", "title": "Singpass and phishing safety", "agency": "GovTech",
     "source_url": "https://www.tech.gov.sg/",
     "text": "Singpass is the national digital identity used to access hundreds of government and private services. Never log in to Singpass through a link sent in a message or by an assistant — always open your own browser and type the official address yourself, and enable Singpass Face Verification and notifications to guard against phishing."},

    # ── CPF (extended) ──
    {"id": "cpf-retirement-sums", "title": "Basic, Full and Enhanced Retirement Sums", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "At age 55 a Retirement Account is created and members set aside a retirement sum that funds CPF LIFE payouts. There are three tiers — Basic (BRS), Full (FRS, which is twice the BRS), and Enhanced (ERS) — with higher sums giving higher monthly payouts. The exact dollar figures rise each year, so check the CPF website for the current cohort's sums."},
    {"id": "cpf-interest", "title": "CPF interest rates and extra interest", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "CPF Ordinary Account savings earn a floor of 2.5% a year while Special, MediSave and Retirement Accounts earn a higher rate pegged to bond yields. Members below 55 earn an extra 1% on the first S$60,000 of combined balances, and those 55 and above earn additional interest on top, boosting retirement savings. Current rates are published quarterly on the CPF site."},
    {"id": "cpf-55-withdrawal", "title": "CPF withdrawals from age 55", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "From age 55, members can withdraw part of their CPF savings — at least a lump sum is available even if the Full Retirement Sum is not met, and more can be withdrawn above the sum set aside. Savings left in CPF continue earning interest, and monthly CPF LIFE payouts start from the payout eligibility age. Apply for withdrawals through the CPF website with Singpass."},
    {"id": "cpf-nomination", "title": "CPF nomination", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "A CPF nomination directs how your CPF savings are distributed when you pass away, bypassing the slower intestacy or probate process. Without a nomination, savings are transferred to the Public Trustee's Office for distribution under intestacy law with an administrative fee. Make or update a nomination online via the CPF website."},
    {"id": "cpf-self-employed-medisave", "title": "MediSave for the self-employed", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "Self-employed persons earning above a yearly net trade income threshold must make compulsory MediSave contributions, even though they have no Ordinary or Special Account obligations. The amount is a percentage of net trade income up to a ceiling, and IRAS/CPF will bill it after income is declared. Voluntary CPF contributions can also earn tax relief."},

    # ── Tax (IRAS, extended) ──
    {"id": "iras-noa", "title": "Notice of Assessment (NOA)", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "The Notice of Assessment (NOA) is IRAS's official statement of your chargeable income, reliefs, and the tax payable for a Year of Assessment. Check it against your own records and file an objection within the stated window if anything is wrong. Payment is usually due about one month from the NOA date unless you are on GIRO instalments."},
    {"id": "iras-mytax-filing", "title": "Filing income tax on myTax Portal", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "Individuals file their income tax return by logging in to myTax Portal with Singpass during the filing season. Employment income under the Auto-Inclusion Scheme is pre-filled; you add other income and claim reliefs. Those on the No-Filing Service only need to verify and confirm their pre-filled details."},
    {"id": "iras-nfs", "title": "No-Filing Service (NFS)", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "Under the No-Filing Service, taxpayers whose income and reliefs are already known to IRAS do not need to file a return — a Notice of Assessment is issued directly. You should still review your details and file changes if you have additional income (such as rental or trade income) or reliefs to update."},
    {"id": "iras-payment-giro", "title": "Paying tax by GIRO", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "GIRO lets you pay income tax, property tax, or other IRAS taxes in interest-free monthly instalments instead of one lump sum, deducted automatically from your bank account. Apply through myTax Portal or your bank; approved GIRO plans spread payment across the year and reduce the risk of late-payment penalties."},
    {"id": "iras-bsd", "title": "Buyer's Stamp Duty (BSD)", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "Buyer's Stamp Duty is payable on the purchase or acquisition of property, calculated on the higher of the price or market value at progressive rates that are higher for the portion of value above set thresholds and for non-residential property. It is due within 14 days of signing; use the IRAS stamp duty calculator for the exact amount."},
    {"id": "iras-absd", "title": "Additional Buyer's Stamp Duty (ABSD)", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "Additional Buyer's Stamp Duty is charged on top of Buyer's Stamp Duty depending on the buyer's residency/citizenship and how many residential properties they already own. Singapore citizens buying their first home are not charged ABSD, while rates rise for second and subsequent properties and for PRs and foreigners. Check the current ABSD rates on the IRAS website."},
    {"id": "iras-rental-income", "title": "Tax on rental income", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "Rental income from letting out property is taxable and must be declared, but you may deduct allowable expenses such as property tax, mortgage interest, and repairs — or claim a simplified deemed expense on residential rent. Keep records of income and expenses, as net rental profit is added to your chargeable income."},
    {"id": "iras-parenthood-rebate", "title": "Parenthood Tax Rebate (PTR)", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "The Parenthood Tax Rebate is a rebate that offsets income tax payable for married, divorced, or widowed parents, given per qualifying child and increasing with birth order. Unlike reliefs it reduces tax directly and any unused amount can be carried forward. It is separate from the Working Mother's Child Relief and Qualifying Child Relief."},
    {"id": "iras-objection", "title": "Objecting to an assessment", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "If you disagree with your Notice of Assessment, you can file an objection through myTax Portal (or by other stated means) within the deadline shown on the notice, explaining what should be corrected. Tax remains payable by the due date while the objection is reviewed, and any overpayment is refunded if the objection succeeds."},
    {"id": "iras-tax-residency", "title": "Tax residency status", "agency": "IRAS",
     "source_url": "https://www.iras.gov.sg/",
     "text": "You are generally a Singapore tax resident for a Year of Assessment if you are a citizen or PR who normally lives here, or a foreigner who stayed or worked in Singapore for at least 183 days in the previous year. Residents are taxed at progressive rates and enjoy reliefs; non-residents are taxed differently, so residency affects the tax you owe."},

    # ── Housing (HDB, extended) ──
    {"id": "hdb-mop", "title": "Minimum Occupation Period (MOP)", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "The Minimum Occupation Period is the number of years (commonly five) you must physically live in your HDB flat before you can sell it on the open market, rent out the whole flat, or buy private property. The MOP is counted from key collection and excludes periods where the flat is not occupied. Selling or subletting before the MOP is generally not allowed."},
    {"id": "hdb-hfe-letter", "title": "HDB Flat Eligibility (HFE) letter", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "The HDB Flat Eligibility (HFE) letter is a single upfront check, applied for on the HDB Flat Portal with Singpass, that tells you your eligibility to buy a new or resale flat, the CPF housing grants you qualify for, and the HDB housing loan amount you can take. You need a valid HFE letter before booking a flat or getting an Option to Purchase."},
    {"id": "hdb-resale-process", "title": "Buying a resale flat", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "Buying a resale flat involves getting an HFE letter, negotiating with the seller who grants an Option to Purchase (OTP), then submitting the resale application to HDB through the HDB Flat Portal for approval and completion. Buyers should budget for the cash-over-valuation gap, stamp duty, and legal fees on top of the flat price."},
    {"id": "hdb-proximity-grant", "title": "Proximity Housing Grant (PHG)", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "The Proximity Housing Grant helps families and singles buying a resale flat to live with or near their parents or married child, encouraging mutual care and support. The grant amount is higher when you live with, rather than merely near, your family, and it is credited to the CPF Ordinary Account. Distance and eligibility rules apply — check the HDB grant page."},
    {"id": "hdb-resale-levy", "title": "Resale levy", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "Second-timer applicants who previously enjoyed a housing subsidy (for example a first BTO flat) must pay a resale levy when buying a second subsidised flat, to reduce the subsidy given twice. The levy is a fixed amount by flat type and is deducted when you take the second flat. It does not apply if your second flat is bought without subsidy."},
    {"id": "hdb-renting-out", "title": "Renting out an HDB flat or bedroom", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "Flat owners can rent out spare bedrooms at any time, but renting out the whole flat is only allowed after completing the Minimum Occupation Period and with HDB's approval, subject to a maximum tenancy period and occupancy caps. Both the flat and the bedroom rental must be registered with HDB, and rental income is taxable."},
    {"id": "hdb-lease-buyback", "title": "Lease Buyback Scheme (LBS)", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "The Lease Buyback Scheme lets eligible elderly flat owners sell part of their flat's remaining lease back to HDB while continuing to live in it, unlocking retirement income that partly tops up CPF for higher CPF LIFE payouts plus a cash bonus. It suits seniors who want to age in place while monetising their flat."},
    {"id": "hdb-vers-sers", "title": "SERS and VERS lease renewal schemes", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "HDB flats sit on 99-year leases. Under the Selective En bloc Redevelopment Scheme (SERS), the government rehouses residents of selected older blocks with compensation; the Voluntary Early Redevelopment Scheme (VERS) will let residents of some older estates vote on early redevelopment. Most flats simply run their lease, so buyers should note the remaining lease when purchasing."},
    {"id": "hdb-upgrading-hip", "title": "Home Improvement Programme (HIP)", "agency": "HDB",
     "source_url": "https://www.hdb.gov.sg/",
     "text": "The Home Improvement Programme upgrades ageing flats with essential repairs (such as pipe replacement and spalling-concrete fixing) and optional improvements, heavily subsidised for Singapore-citizen households. Estate-wide upgrading programmes are announced by HDB and town councils; residents usually vote before major works proceed."},

    # ── Employment (MOM, extended) ──
    {"id": "mom-cpf-rates", "title": "CPF contribution rates by age", "agency": "MOM",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "For employees who are citizens or PRs, both employer and employee contribute a percentage of monthly wages to CPF, up to the Ordinary Wage ceiling. The combined rate is highest for younger workers and steps down in older age bands as more goes toward retirement and healthcare. Refer to the CPF contribution-rate tables for the exact percentages by age."},
    {"id": "mom-ep-compass", "title": "Employment Pass and COMPASS", "agency": "MOM",
     "source_url": "https://www.mom.gov.sg/",
     "text": "The Employment Pass is for foreign professionals earning above a qualifying monthly salary that rises with age and sector. Applications are also assessed under COMPASS, a points framework scoring salary, qualifications, diversity, and support for local employment. Employers apply on the MOM website; passes are renewable if criteria continue to be met."},
    {"id": "mom-wica", "title": "Work Injury Compensation (WICA)", "agency": "MOM",
     "source_url": "https://www.mom.gov.sg/",
     "text": "The Work Injury Compensation Act lets employees claim for injuries or diseases arising from work without having to prove fault, covering medical expenses, lost wages during medical leave, and lump-sum compensation for permanent incapacity or death. Employers must carry WICA insurance for covered workers, and claims are lodged with MOM."},
    {"id": "mom-pwm", "title": "Progressive Wage Model (PWM)", "agency": "MOM",
     "source_url": "https://www.mom.gov.sg/",
     "text": "The Progressive Wage Model sets minimum wages that rise with skills and productivity for workers in covered sectors such as cleaning, security, and landscaping, and for occupations like administrators and drivers. Firms employing foreign workers must pay all local employees at least the Local Qualifying Salary. It lifts lower-wage workers' pay along a career ladder."},
    {"id": "mom-payslip", "title": "Itemised payslips and key employment terms", "agency": "MOM",
     "source_url": "https://www.mom.gov.sg/",
     "text": "Employers must issue itemised payslips to employees covered by the Employment Act, showing salary, allowances, deductions, overtime, and CPF, and must give Key Employment Terms in writing. These records help resolve salary disputes, which can be brought to MOM or the Tripartite Alliance for Dispute Management."},
    {"id": "mom-workfare", "title": "Workfare Income Supplement (WIS)", "agency": "MOM",
     "source_url": "https://www.mom.gov.sg/",
     "text": "The Workfare Income Supplement tops up the income and CPF of lower-wage Singaporean workers aged 30 and above (and persons with disabilities of any age) who meet income and property criteria. Employees are paid automatically, while self-employed persons must declare income and contribute MediSave to qualify. Payouts come partly in cash and partly to CPF."},

    # ── Benefits & schemes (extended) ──
    {"id": "assurance-package", "title": "Assurance Package", "agency": "GovBenefits / MOF",
     "source_url": "https://www.govbenefits.gov.sg/",
     "text": "The Assurance Package is a set of government payouts that helps Singaporeans offset the cost of living and the GST increase, including cash payments, MediSave top-ups, CDC vouchers, and support for seniors. Eligibility and amounts depend on age, income, and property; check GovBenefits or SupportGoWhere for what you will receive and when."},
    {"id": "gst-voucher", "title": "GST Voucher scheme", "agency": "GovBenefits / MOF",
     "source_url": "https://www.govbenefits.gov.sg/",
     "text": "The permanent GST Voucher scheme helps lower- and middle-income Singaporeans through Cash (for daily expenses), MediSave top-ups for seniors, and U-Save rebates that offset utility bills for HDB households. Eligibility is based on income, the Annual Value of your home, and property ownership. Payouts are made in set months each year."},
    {"id": "silver-support", "title": "Silver Support Scheme", "agency": "CPF / GovBenefits",
     "source_url": "https://www.govbenefits.gov.sg/",
     "text": "The Silver Support Scheme gives quarterly cash payments to seniors who had low incomes through life and have little family support, identified using CPF contribution history, housing type, and household income. Eligible seniors are notified and paid automatically — there is no need to apply. It supplements other retirement support such as CPF payouts."},
    {"id": "majulah-package", "title": "Majulah Package", "agency": "CPF / GovBenefits",
     "source_url": "https://www.govbenefits.gov.sg/",
     "text": "The Majulah Package supports 'young seniors' — Singaporeans born in or before a stated year — with an Earn and Save Bonus for those still working, a one-off Retirement Savings Bonus for those with lower CPF balances, and a MediSave Bonus. It is aimed at helping this cohort strengthen retirement and healthcare savings closer to retirement age."},
    {"id": "supportgowhere", "title": "SupportGoWhere", "agency": "GovTech / MSF",
     "source_url": "https://supportgowhere.life.gov.sg/",
     "text": "SupportGoWhere is a national one-stop site that helps residents discover government support schemes and benefits they may be eligible for, from cost-of-living payouts to family and senior assistance. Its eligibility checker and benefits calculator let you estimate what you can claim, and it links out to the official application channels."},
    {"id": "lifesg", "title": "LifeSG app", "agency": "GovTech",
     "source_url": "https://www.life.gov.sg/",
     "text": "LifeSG is the government's personal services app that gives residents a single place to access many government transactions and benefits — checking payouts, personal records, reminders for life events, and links to services across agencies — using Singpass. It bundles frequently needed digital government services in one mobile app."},

    # ── Healthcare (extended) ──
    {"id": "careshield-life", "title": "CareShield Life", "agency": "MOH",
     "source_url": "https://www.moh.gov.sg/",
     "text": "CareShield Life is a national long-term-care insurance that provides monthly cash payouts for life if you become severely disabled and unable to perform several daily activities. It replaced the older ElderShield for younger cohorts, premiums can be paid from MediSave, and payouts help meet care costs at home or in a facility."},
    {"id": "pioneer-merdeka", "title": "Pioneer and Merdeka Generation packages", "agency": "MOH",
     "source_url": "https://www.moh.gov.sg/",
     "text": "The Pioneer Generation and Merdeka Generation packages give older Singaporeans lifelong benefits such as outpatient subsidies, MediSave top-ups, and CareShield/MediShield premium support, recognising cohorts born in defined periods. Benefits are tied to your birth year and citizenship and are applied automatically at participating clinics."},
    {"id": "medifund", "title": "MediFund", "agency": "MOH",
     "source_url": "https://www.moh.gov.sg/",
     "text": "MediFund is a government endowment safety net that helps needy Singaporeans who still cannot afford their bills after government subsidies, MediShield Life, and MediSave. Applications are made at the medical institution's business office or medical social worker, who assess the patient's financial situation before granting assistance."},
    {"id": "integrated-shield", "title": "Integrated Shield Plans", "agency": "MOH",
     "source_url": "https://www.moh.gov.sg/",
     "text": "Integrated Shield Plans are optional private insurance that wraps around MediShield Life to give higher coverage, such as private-hospital or higher-ward stays. Premiums are partly payable from MediSave up to Additional Withdrawal Limits, with the cash portion paid out of pocket. Riders can reduce co-payment but raise premiums."},
    {"id": "screen-for-life", "title": "Screen for Life", "agency": "MOH",
     "source_url": "https://www.healthhub.sg/",
     "text": "Screen for Life is the national health-screening programme offering subsidised checks for chronic diseases (like diabetes and high blood pressure) and selected cancers to eligible citizens and PRs, with heavily subsidised or free screening for lower-income and Pioneer/Merdeka groups. Book through participating CHAS clinics or Healthier SG."},

    # ── Education (extended) ──
    {"id": "moe-kindergarten", "title": "MOE Kindergartens", "agency": "MOE",
     "source_url": "https://www.moe.gov.sg/",
     "text": "MOE Kindergartens provide affordable, quality pre-school education for children in the two years before Primary 1, with priority and fee subsidies for Singapore citizens and lower-income families. Registration runs annually; places are balloted where demand exceeds supply. Other licensed pre-schools are supported by ECDA subsidies."},
    {"id": "edusave", "title": "Edusave scheme", "agency": "MOE",
     "source_url": "https://www.moe.gov.sg/",
     "text": "Edusave gives every Singaporean school-age child an account with annual government contributions that can pay for enrichment programmes and approved school charges. Edusave also funds awards and bursaries recognising achievement, good conduct, and financial need. Balances follow the child through their school years."},
    {"id": "moe-jae", "title": "Joint Admissions Exercise (JAE)", "agency": "MOE",
     "source_url": "https://www.moe.gov.sg/",
     "text": "The Joint Admissions Exercise is how students posting after national examinations apply for places in junior colleges, Millennia Institute, polytechnics, and ITE, ranking up to a set number of course choices. Posting is based on results and choice order. Students can also enter through early-admission exercises before results are released."},
    {"id": "moe-psle-posting", "title": "PSLE and secondary posting", "agency": "MOE",
     "source_url": "https://www.moe.gov.sg/",
     "text": "The Primary School Leaving Examination scores are now reported in Achievement Levels, and students are posted to secondary schools through choice order and Full Subject-Based Banding, which lets them take subjects at different levels based on strengths. The old Express/Normal streams have been merged into subject-based banding."},
    {"id": "moe-post-secondary", "title": "Post-secondary pathways (ITE, poly, university)", "agency": "MOE",
     "source_url": "https://www.moe.gov.sg/",
     "text": "After secondary school, students can progress through the ITE, polytechnic, or junior-college route toward the autonomous universities, with multiple bridges between them. Admission to universities considers academic results plus aptitude-based routes. Government tuition-grant subsidies and bursaries lower fees for eligible Singaporeans."},
    {"id": "cpf-education-scheme", "title": "CPF Education Loan Scheme", "agency": "CPF",
     "source_url": "https://www.cpf.gov.sg/",
     "text": "The CPF Education Loan Scheme lets students use their own or a family member's CPF Ordinary Account savings to pay subsidised tuition fees at approved local institutions, subject to a withdrawal limit. The amount used must be repaid in cash with interest to the CPF account after graduation, restoring retirement savings."},

    # ── Transport (LTA, extended) ──
    {"id": "lta-simplygo", "title": "SimplyGo and fare payment", "agency": "LTA",
     "source_url": "https://www.lta.gov.sg/",
     "text": "SimplyGo lets commuters pay bus and train fares by tapping a contactless bank card, mobile wallet, or a SimplyGo EZ-Link card, with fares charged to the linked account and viewable in the SimplyGo app. Concession cardholders continue to enjoy their concessionary fares. It replaces the need to top up stored value for many riders."},
    {"id": "lta-erp", "title": "Electronic Road Pricing (ERP)", "agency": "LTA",
     "source_url": "https://www.lta.gov.sg/",
     "text": "Electronic Road Pricing charges motorists a fee to use certain roads during peak hours to manage congestion, deducted from an in-vehicle unit. Charges vary by location, time, and vehicle type, and are revised as traffic conditions change. A satellite-based system is being rolled out to modernise how road usage is priced."},
    {"id": "lta-arf-omv", "title": "Vehicle taxes: ARF and OMV", "agency": "LTA",
     "source_url": "https://www.lta.gov.sg/",
     "text": "Buying a car in Singapore involves the Open Market Value (OMV, the vehicle's assessed import value), the Additional Registration Fee (ARF, a tax charged as a rising percentage of OMV), plus registration fees, COE, and GST. These make the on-the-road price much higher than the base vehicle cost. The LTA and OneMotoring sites explain the components."},
    {"id": "lta-ev-incentives", "title": "Electric vehicle incentives", "agency": "LTA",
     "source_url": "https://www.lta.gov.sg/",
     "text": "Singapore encourages electric vehicles through registration-fee rebates and adjusted road tax so that cleaner cars are more affordable, while expanding public charging points nationwide. Incentive schemes and road-tax formulas for EVs are periodically updated, so check the LTA and OneMotoring pages for the current rates before buying."},
    {"id": "lta-active-mobility", "title": "Cycling and active-mobility rules", "agency": "LTA",
     "source_url": "https://www.lta.gov.sg/",
     "text": "Rules under the Active Mobility Act govern where bicycles, e-bikes, and personal mobility devices (PMDs) may be used and their speed limits, with PMDs restricted mainly to cycling paths and requiring device registration and safety standards. Riding non-compliant devices or on prohibited paths can attract fines to keep paths safe for pedestrians."},

    # ── Immigration & identity (ICA, extended) ──
    {"id": "ica-pr-application", "title": "Permanent Residence application", "agency": "ICA",
     "source_url": "https://www.ica.gov.sg/",
     "text": "Applications for Singapore Permanent Residence are submitted online to ICA, commonly under the professional/technical/skilled worker or family schemes, with supporting documents on employment, income, and family. Approval is discretionary and considers factors such as economic contribution and ability to integrate. Processing typically takes several months."},
    {"id": "ica-passes-ltvp-dp", "title": "Long-Term Visit Pass and Dependant's Pass", "agency": "ICA",
     "source_url": "https://www.ica.gov.sg/",
     "text": "The Dependant's Pass lets eligible spouses and children of Employment/S Pass holders live in Singapore, while the Long-Term Visit Pass covers other family members such as common-law spouses or parents. These passes are tied to the sponsor's pass and must be applied for by the employer or sponsor; some allow work with an additional letter of consent."},
    {"id": "ica-reentry-permit", "title": "Re-Entry Permit for PRs", "agency": "ICA",
     "source_url": "https://www.ica.gov.sg/",
     "text": "A Permanent Resident must hold a valid Re-Entry Permit (REP) to retain PR status while travelling in and out of Singapore; letting it lapse while overseas can cause loss of PR status. REPs are issued for a period and renewed online through ICA before expiry, taking into account the PR's contributions and ties to Singapore."},
    {"id": "ica-birth-death", "title": "Birth and death registration", "agency": "ICA",
     "source_url": "https://www.ica.gov.sg/",
     "text": "Births and deaths in Singapore are registered with ICA, increasingly through digital services so that hospitals transmit records and parents or next of kin verify details online with Singpass. A birth certificate is needed for schemes like Baby Bonus, while a death certificate is required to settle the estate and CPF matters."},

    # ── Civic, digital & business (extended) ──
    {"id": "corppass", "title": "Corppass for businesses", "agency": "GovTech",
     "source_url": "https://www.corppass.gov.sg/",
     "text": "Corppass is the corporate digital identity that businesses use to transact with government agencies online — filing taxes, applying for licences, and making CPF submissions. A company appoints administrators who assign staff access to specific e-services. It is separate from personal Singpass and is required for most business-to-government transactions."},
    {"id": "myinfo", "title": "Myinfo", "agency": "GovTech",
     "source_url": "https://www.singpass.gov.sg/",
     "text": "Myinfo is a Singpass service that lets citizens and residents pre-fill online forms with verified personal data (like address and income) held by the government, so they do not have to key in or upload documents repeatedly. You consent each time before your data is shared with a participating government or private service."},
    {"id": "govbenefits", "title": "GovBenefits portal", "agency": "GovBenefits",
     "source_url": "https://www.govbenefits.gov.sg/",
     "text": "GovBenefits is a portal where Singaporeans can view and check government payouts and benefits credited to them — such as Assurance Package cash, GST Vouchers, and other cost-of-living support — in one place with Singpass. It helps residents confirm what they are receiving and the payout schedule without visiting multiple agency sites."},
    {"id": "scamshield", "title": "ScamShield and scam prevention", "agency": "GovTech / SPF",
     "source_url": "https://www.scamshield.gov.sg/",
     "text": "ScamShield is a national app and service that helps block scam calls and filter scam messages, backed by a central registry of reported scam numbers. Residents are urged to verify suspicious requests, never share Singpass or bank credentials or OTPs, and report scams to the police anti-scam hotline. Government agencies never ask for passwords over calls or chats."},
    {"id": "acra-business", "title": "Registering a business with ACRA", "agency": "ACRA",
     "source_url": "https://www.acra.gov.sg/",
     "text": "New businesses and companies are registered with the Accounting and Corporate Regulatory Authority through the BizFile portal using Singpass or Corppass. A sole proprietorship or company must be registered before it can operate, and companies have ongoing filing duties such as annual returns. Fees and requirements are listed on the ACRA website."},
    {"id": "rom-marriage", "title": "Marriage registration (ROM/ROMM)", "agency": "MSF / ROM",
     "source_url": "https://www.marriage.gov.sg/",
     "text": "Civil marriages are registered with the Registry of Marriages (ROM) and Muslim marriages with the Registry of Muslim Marriages (ROMM). Couples file a notice of marriage online, meet eligibility and minimum-age rules, and solemnise within the validity window. A marriage certificate supports applications for housing and other family benefits."},
    {"id": "legal-aid", "title": "Legal Aid Bureau", "agency": "MinLaw",
     "source_url": "https://lab.mlaw.gov.sg/",
     "text": "The Legal Aid Bureau provides subsidised legal advice and representation in civil matters to Singaporeans and PRs who pass a means test on income and assets. It helps with matters such as divorce, maintenance, and probate. Criminal cases are supported separately through a criminal legal-aid scheme."},
    {"id": "small-claims", "title": "Small Claims Tribunals", "agency": "Judiciary",
     "source_url": "https://www.judiciary.gov.sg/",
     "text": "The Small Claims Tribunals resolve certain disputes quickly and cheaply — such as claims over goods, services, or residential tenancy — up to a monetary limit, without the need for lawyers. Claims are filed online through the Community Justice and Tribunals System, and parties first attempt mediation before a tribunal hearing."},

    # ── Environment (NEA, extended) ──
    {"id": "nea-haze", "title": "Haze and air-quality advisories", "agency": "NEA",
     "source_url": "https://www.nea.gov.sg/",
     "text": "During haze episodes, NEA publishes the Pollutant Standards Index (PSI) and PM2.5 readings and issues health advisories on outdoor activity for the general public and vulnerable groups. Readings are updated regularly on the NEA website and myENV app, and schools and workplaces refer to them when deciding on precautions."},
    {"id": "nea-dengue", "title": "Dengue prevention", "agency": "NEA",
     "source_url": "https://www.nea.gov.sg/",
     "text": "NEA tracks dengue clusters and urges residents to remove stagnant water where Aedes mosquitoes breed, using the 'Mozzie Wipeout' steps. Homeowners in cluster areas may receive inspections, and breeding of mosquitoes can attract fines. Cluster maps and case counts are published on the NEA website and myENV app."},
    {"id": "nea-recycling", "title": "Recycling and the blue bin", "agency": "NEA",
     "source_url": "https://www.nea.gov.sg/",
     "text": "Households can recycle paper, plastic, glass, and metal in the common blue recycling bins, keeping items clean and dry and avoiding food-contaminated or non-recyclable waste that contaminates the batch. NEA runs recycling education and e-waste and battery collection points to raise Singapore's recycling rate under the Zero Waste Masterplan."},
]


def corpus_size() -> int:
    return len(KNOWLEDGE_BASE)


def _corpus_fingerprint() -> str:
    """Stable hash of the corpus text + embedding config, so the disk cache is invalidated (and the
    corpus re-embedded) whenever a chunk's text, the model, or the dimension changes."""
    h = hashlib.sha256()
    h.update(f"{_EMBED_MODEL}|{_EMBED_DIM}".encode("utf-8"))
    for doc in KNOWLEDGE_BASE:
        h.update(("\x1f".join((doc["id"], doc["title"], doc["text"])) + "\x1e").encode("utf-8"))
    return h.hexdigest()


def _get_client():
    # Reuse the chat module's lazily-constructed Gemini client so we don't create a second one or
    # require credentials at import time (the test suite imports tools without live creds).
    from tools.chat import _get_client as _chat_client
    return _chat_client()


def _embed(texts: list, task_type: str) -> list:
    """Embeds a batch of texts with gemini-embedding-001 at _EMBED_DIM dimensions. `task_type` is
    RETRIEVAL_DOCUMENT for corpus chunks and RETRIEVAL_QUERY for the user query — this asymmetry
    measurably sharpens retrieval ranking. Batched to stay well under request-size limits."""
    from google.genai import types
    cfg = types.EmbedContentConfig(task_type=task_type, output_dimensionality=_EMBED_DIM)
    vectors = []
    for start in range(0, len(texts), 20):
        batch = texts[start:start + 20]
        resp = _get_client().models.embed_content(model=_EMBED_MODEL, contents=batch, config=cfg)
        vectors.extend([list(e.values) for e in resp.embeddings])
    return vectors


def _cosine(a: list, b: list) -> float:
    """Pure-Python cosine similarity (the corpus is small enough that numpy isn't worth a dep)."""
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


# Module-level cache of the corpus vectors, aligned by index with KNOWLEDGE_BASE.
_corpus_vectors = None


def _load_cached_vectors():
    """Returns cached corpus vectors from disk if the fingerprint matches the current corpus, else
    None. Non-fatal on any read/parse error — we just re-embed."""
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            snap = json.load(f)
        if snap.get("fingerprint") == _corpus_fingerprint() and len(snap.get("vectors", [])) == len(KNOWLEDGE_BASE):
            return snap["vectors"]
    except (OSError, ValueError, KeyError):
        pass
    return None


def _save_cached_vectors(vectors: list) -> None:
    try:
        os.makedirs(_DISK_CACHE_DIR, exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"fingerprint": _corpus_fingerprint(), "model": _EMBED_MODEL,
                       "dim": _EMBED_DIM, "vectors": vectors}, f)
    except (OSError, TypeError, ValueError) as e:
        print(f"  [kb] embedding cache save skipped: {type(e).__name__}: {e}")


def ensure_corpus_embedded() -> bool:
    """Loads the corpus embeddings into memory — from disk cache if fresh, else by embedding the
    corpus once and caching the result. Returns True if embeddings are ready, False if they could
    not be produced (e.g. embedding API unavailable). Safe to call repeatedly and concurrently-ish;
    the worst case under a race is embedding twice, which is harmless."""
    global _corpus_vectors
    if _corpus_vectors is not None:
        return True

    cached = _load_cached_vectors()
    if cached is not None:
        _corpus_vectors = cached
        return True

    try:
        print(f"  \033[90m[kb] Embedding {len(KNOWLEDGE_BASE)} knowledge-base chunks ({_EMBED_MODEL}, {_EMBED_DIM}d)...\033[0m")
        vectors = _embed([d["text"] for d in KNOWLEDGE_BASE], task_type="RETRIEVAL_DOCUMENT")
        _corpus_vectors = vectors
        _save_cached_vectors(vectors)
        return True
    except Exception as e:
        logger.warning(f"Knowledge-base embedding unavailable: {type(e).__name__}: {e}")
        return False


def prewarm_knowledge_base() -> None:
    """Startup hook: embed the corpus ahead of the first query. Best-effort — failures are logged
    and the tool falls back to lazy embedding (or a graceful message) at query time."""
    try:
        ok = ensure_corpus_embedded()
        if ok:
            print(f"\033[33m[kb] Knowledge base ready: {len(KNOWLEDGE_BASE)} chunks embedded/cached.\033[0m")
    except Exception as e:
        print(f"\033[31m[kb] Pre-warm skipped ({type(e).__name__}: {e}) — will embed lazily on first query.\033[0m")


def retrieve(query: str, top_k: int = 3, min_score: float = 0.30) -> list:
    """Returns up to top_k corpus chunks most similar to `query`, each as a dict with an added
    `score`, filtered to those above min_score. Empty list if embeddings are unavailable or nothing
    clears the threshold. This is the programmatic entry point used by both the tool wrapper and the
    unit tests (which inject deterministic vectors)."""
    if not query or not query.strip():
        return []
    if not ensure_corpus_embedded():
        return []
    try:
        query_vec = _embed([query], task_type="RETRIEVAL_QUERY")[0]
    except Exception as e:
        logger.warning(f"Query embedding failed: {type(e).__name__}: {e}")
        return []

    scored = []
    for doc, vec in zip(KNOWLEDGE_BASE, _corpus_vectors):
        score = _cosine(query_vec, vec)
        if score >= min_score:
            hit = dict(doc)
            hit["score"] = score
            scored.append(hit)
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:top_k]


def search_knowledge_base(context_query: str) -> str:
    """Tool: Retrieves grounded, cited guidance from MerlionOS's curated Singapore civic knowledge
    base. Use this for general policy, scheme, or eligibility questions (e.g. "difference between
    BTO and resale", "how does CPF LIFE work", "who must file income tax") that no single agency
    tool specifically answers. Always cite the returned source URLs in your reply.

    Args:
        context_query: The citizen's question or the specific civic topic to look up.
    """
    hits = retrieve(context_query, top_k=3)
    if not hits:
        return ("--- [KNOWLEDGE BASE] ---\n"
                "No sufficiently relevant entry was found in the curated civic knowledge base for "
                "this query. Answer from other tools or official sources, and avoid asserting "
                "unverified specifics.")
    lines = ["--- [MERLIONOS CIVIC KNOWLEDGE BASE — retrieved, cite these sources] ---"]
    for i, hit in enumerate(hits, 1):
        lines.append(
            f"\n[{i}] {hit['title']} ({hit['agency']}) — relevance {hit['score']:.2f}\n"
            f"{hit['text']}\n"
            f"Source: {hit['source_url']}"
        )
    return "\n".join(lines)
