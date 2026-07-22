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
