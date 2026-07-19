"""
MerlionOS Tools Package
-----------------------
Split from the original monolithic tools.py into topic modules.
This __init__.py re-exports every public symbol so that existing callers
(server.py, mcp_server.py, main.py) continue to work without any changes.
"""

# ── Shared utilities ──────────────────────────────────────────────────────────
from tools.core import (
    _data_gov_sg_headers,
    _cache_synced_at,
    _sgt_now,
    _annual_dataset_is_stale,
    _DISK_CACHE_DIR,
    _disk_cache_load,
    _disk_cache_save,
)

# ── Civic & identity tools ────────────────────────────────────────────────────
from tools.civic import (
    GOV_DIRECTORY,
    query_immigration_and_identity,
    query_singapore_journey_onboarding,
    query_iras_tax_and_cpf_ledgers,
    query_welfare_and_skills_credits,
    query_supplementary_civic_utilities,
)

# ── Search & scraping tools ───────────────────────────────────────────────────
from tools.search import (
    search_singapore_government,
    scrape_government_page,
    call_tool_robustly,
)

# ── Environment / weather advisory ───────────────────────────────────────────
from tools.environment import (
    get_singapore_live_environment_advisory,
)

# ── Job market, vacancies & retrenchment ─────────────────────────────────────
from tools.jobs import (
    compute_job_market_history,
    get_retrenchment_synced_at,
    query_singapore_job_statistics_via_bigquery,
    query_singapore_retrenchment_advisory,
)

# ── Housing: BTO & resale ─────────────────────────────────────────────────────
from tools.housing import (
    compute_hdb_resale_stats,
    query_hdb_bto_launches_and_grants,
    query_hdb_resale_price_trends,
)

# ── Transport: COE ────────────────────────────────────────────────────────────
from tools.transport import (
    get_coe_synced_at,
    query_coe_bidding_results,
)

# ── Wages: salary growth & occupational wage survey ──────────────────────────
from tools.wages import (
    compute_occupational_wage_insights,
    get_occ_wage_synced_at,
    query_occupational_wage_insights,
)

__all__ = [
    # core
    "_data_gov_sg_headers", "_cache_synced_at", "_sgt_now",
    "_annual_dataset_is_stale", "_DISK_CACHE_DIR", "_disk_cache_load", "_disk_cache_save",
    # civic
    "GOV_DIRECTORY",
    "query_immigration_and_identity", "query_singapore_journey_onboarding",
    "query_iras_tax_and_cpf_ledgers", "query_welfare_and_skills_credits",
    "query_supplementary_civic_utilities",
    # search
    "search_singapore_government", "scrape_government_page", "call_tool_robustly",
    # environment
    "get_singapore_live_environment_advisory",
    # jobs
    "compute_job_market_history", "get_retrenchment_synced_at",
    "query_singapore_job_statistics_via_bigquery", "query_singapore_retrenchment_advisory",
    # housing
    "compute_hdb_resale_stats", "query_hdb_bto_launches_and_grants",
    "query_hdb_resale_price_trends",
    # transport
    "get_coe_synced_at", "query_coe_bidding_results",
    # wages
    "compute_occupational_wage_insights",
    "get_occ_wage_synced_at",
    "query_occupational_wage_insights",
]
