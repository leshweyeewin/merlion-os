"""
MerlionOS Tools Package
-----------------------
Split from the original monolithic tools.py into topic modules.
This __init__.py re-exports every public symbol so that existing callers
(server.py, mcp_server.py) continue to work without any changes.
"""

# ── Shared utilities ──────────────────────────────────────────────────────────
from tools.core import (
    _data_gov_sg_headers,
    _cache_synced_at,
    _cache_get,
    _cache_set,
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
    fetch_ica_media_releases,
    fetch_iras_due_dates,
)

# ── Search & scraping tools ───────────────────────────────────────────────────
from tools.search import (
    search_singapore_government,
    scrape_government_page,
    call_tool_robustly,
    GOV_CHANNELS,
    COMMUNITY_CHANNELS,
    scrape_one_telegram_channel,
    scrape_one_telegram_channel_24h,
)

# ── Environment / weather advisory ───────────────────────────────────────────
from tools.environment import (
    get_singapore_live_environment_advisory,
    fetch_weather_data,
    fetch_pub_flood_alerts,
)

# ── Job market, vacancies & retrenchment ─────────────────────────────────────
from tools.jobs import (
    compute_job_market_history,
    get_retrenchment_synced_at,
    resolve_job_sector,
    compute_job_sector_stats,
    compute_retrenchment_stats,
    compute_trend_break_reason,
    compute_sector_divergence_reason,
    compute_retrenchment_deviation_reason,
    format_job_trend_line,
    format_hiring_pressure_display,
    format_cagr_trend_display,
    format_retrenchment_headline,
    query_singapore_job_statistics_via_bigquery,
    query_singapore_retrenchment_advisory,
)

# ── Housing: BTO & resale ─────────────────────────────────────────────────────
from tools.housing import (
    compute_hdb_resale_stats,
    compute_hdb_resale_history,
    compute_resale_mix_shift_reason,
    query_hdb_bto_launches_and_grants,
    query_hdb_resale_price_trends,
    scrape_hdb_news,
)

# ── Transport: COE ────────────────────────────────────────────────────────────
from tools.transport import (
    compute_coe_premium_history,
    get_coe_synced_at,
    compute_coe_bidding_stats,
    compute_coe_movement_reason,
    format_coe_momentum_display,
    format_coe_exercise_display,
    query_coe_bidding_results,
    MRT_LINE_META,
    fetch_lta_train_alerts,
    fetch_lta_taxi_availability,
)

# ── Wages: salary growth & occupational wage survey ──────────────────────────
from tools.wages import (
    compute_occupational_wage_insights,
    compute_tech_wage_growth_reason,
    query_occupational_wage_insights,
)

# ── Chat orchestration ────────────────────────────────────────────────────────
from tools.chat import (
    run_chat_loop,
    run_chat_stream,
    ChatMessage,
    ChatRequest,
    ToolLog,
    ChatResponse,
)

__all__ = [
    # core
    "_data_gov_sg_headers", "_cache_synced_at", "_cache_get", "_cache_set", "_sgt_now",
    "_annual_dataset_is_stale", "_DISK_CACHE_DIR", "_disk_cache_load", "_disk_cache_save",
    # civic
    "GOV_DIRECTORY",
    "query_immigration_and_identity", "query_singapore_journey_onboarding",
    "query_iras_tax_and_cpf_ledgers", "query_welfare_and_skills_credits",
    "query_supplementary_civic_utilities",
    "fetch_ica_media_releases", "fetch_iras_due_dates",
    # search
    "search_singapore_government", "scrape_government_page", "call_tool_robustly",
    "GOV_CHANNELS", "COMMUNITY_CHANNELS",
    "scrape_one_telegram_channel", "scrape_one_telegram_channel_24h",
    # environment
    "get_singapore_live_environment_advisory",
    "fetch_weather_data", "fetch_pub_flood_alerts",
    # jobs
    "compute_job_market_history", "get_retrenchment_synced_at",
    "resolve_job_sector", "compute_job_sector_stats", "compute_retrenchment_stats",
    "compute_trend_break_reason", "compute_sector_divergence_reason", "compute_retrenchment_deviation_reason",
    "format_job_trend_line", "format_hiring_pressure_display",
    "format_cagr_trend_display", "format_retrenchment_headline",
    "query_singapore_job_statistics_via_bigquery", "query_singapore_retrenchment_advisory",
    # housing
    "compute_hdb_resale_stats", "compute_hdb_resale_history", "compute_resale_mix_shift_reason",
    "query_hdb_bto_launches_and_grants", "query_hdb_resale_price_trends",
    "scrape_hdb_news",
    # transport
    "compute_coe_premium_history", "get_coe_synced_at",
    "compute_coe_bidding_stats", "compute_coe_movement_reason",
    "format_coe_momentum_display", "format_coe_exercise_display",
    "query_coe_bidding_results",
    "MRT_LINE_META", "fetch_lta_train_alerts", "fetch_lta_taxi_availability",
    # wages
    "compute_occupational_wage_insights",
    "compute_tech_wage_growth_reason",
    "query_occupational_wage_insights",
    # chat
    "run_chat_loop",
    "run_chat_stream",
    "ChatMessage",
    "ChatRequest",
    "ToolLog",
    "ChatResponse",
]
