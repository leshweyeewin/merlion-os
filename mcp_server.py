"""
MerlionOS FastMCP Server
Exposes Singapore digital services, directory search, and gov.sg scraping as standardized MCP tools.
"""

from mcp.server.fastmcp import FastMCP
from tools import (
    query_immigration_and_identity,
    query_singapore_journey_onboarding,
    query_iras_tax_and_cpf_ledgers,
    query_welfare_and_skills_credits,
    query_supplementary_civic_utilities,
    search_singapore_government,
    scrape_government_page,
    get_singapore_live_environment_advisory,
    query_singapore_job_statistics_via_bigquery,
    query_hdb_bto_launches_and_grants,
    query_singapore_retrenchment_advisory,
    query_coe_bidding_results,
    query_hdb_resale_price_trends,
    query_occupational_wage_insights
)

# Initialize FastMCP Server
mcp = FastMCP("MerlionOS-Singapore-Services")

@mcp.tool(name="query_immigration_and_identity")
def mcp_query_immigration_and_identity(context_query: str) -> str:
    """Handles ICA services including citizenship status, passport renewal, and MyICA appointments."""
    return query_immigration_and_identity(context_query)

@mcp.tool(name="query_singapore_journey_onboarding")
def mcp_query_singapore_journey_onboarding(context_query: str) -> str:
    """Tracks mandatory Singapore Journey milestones for new citizens during their In-Principle Approval (IPA) window."""
    return query_singapore_journey_onboarding(context_query)

@mcp.tool(name="query_iras_tax_and_cpf_ledgers")
def mcp_query_iras_tax_and_cpf_ledgers(context_query: str) -> str:
    """Processes financial obligations and assets spanning IRAS Inland Revenue and CPF boards."""
    return query_iras_tax_and_cpf_ledgers(context_query)

@mcp.tool(name="query_welfare_and_skills_credits")
def mcp_query_welfare_and_skills_credits(context_query: str) -> str:
    """Manages household subsidies, RedeemSG vouchers, and MySkillsFuture learning accounts."""
    return query_welfare_and_skills_credits(context_query)

@mcp.tool(name="query_supplementary_civic_utilities")
def mcp_query_supplementary_civic_utilities(context_query: str) -> str:
    """Manages vital civic accounts including Elections Department (ELD), HealthHub, and SP Group utilities."""
    return query_supplementary_civic_utilities(context_query)

@mcp.tool(name="search_singapore_government")
def mcp_search_singapore_government(query: str) -> str:
    """Searches the Singapore government services directory for agencies or services matching the query."""
    return search_singapore_government(query)

@mcp.tool(name="scrape_government_page")
def mcp_scrape_government_page(url: str) -> str:
    """Scrapes text content from an official Singapore government website (.gov.sg) to retrieve up-to-date information."""
    return scrape_government_page(url)

@mcp.tool(name="get_singapore_live_environment_advisory")
def mcp_get_singapore_live_environment_advisory(context_query: str = "general") -> str:
    """Retrieves live Singapore environment advisories, including weather forecasts and PSI (air quality index) from data.gov.sg."""
    return get_singapore_live_environment_advisory(context_query)

@mcp.tool(name="query_singapore_job_statistics_via_bigquery")
def mcp_query_singapore_job_statistics_via_bigquery(context_query: str = "general") -> str:
    """Queries Singapore's real public job vacancy statistics (MOM, via data.gov.sg) with a YoY trend, next-year forecast, a Hiring Pressure Index (vacancies vs. same-year retrenchments in the same industries), and a multi-year CAGR trend-break check (accelerating/decelerating vs. the sector's own growth rate)."""
    return query_singapore_job_statistics_via_bigquery(context_query)

@mcp.tool(name="query_hdb_bto_launches_and_grants")
def mcp_query_hdb_bto_launches_and_grants(context_query: str = "general") -> str:
    """Processes upcoming HDB BTO launches, application cycles, CPF Enhanced Housing Grants (EHG) eligibility, and pricing tables."""
    return query_hdb_bto_launches_and_grants(context_query)

@mcp.tool(name="query_singapore_retrenchment_advisory")
def mcp_query_singapore_retrenchment_advisory(context_query: str = "general") -> str:
    """Retrieves Singapore's real quarterly retrenchment statistics (MOM, via data.gov.sg) and the top affected industries."""
    return query_singapore_retrenchment_advisory(context_query)

@mcp.tool(name="query_coe_bidding_results")
def mcp_query_coe_bidding_results(context_query: str = "general") -> str:
    """Retrieves Singapore's latest COE (Certificate of Entitlement) bidding results and premiums by vehicle category, plus a demand-momentum read per category (round-over-round premium change and bids-to-quota oversubscription ratio)."""
    return query_coe_bidding_results(context_query)

@mcp.tool(name="query_hdb_resale_price_trends")
def mcp_query_hdb_resale_price_trends(context_query: str = "general") -> str:
    """Retrieves Singapore's real HDB resale flat transaction data with islandwide median price, YoY change, and the priciest towns."""
    return query_hdb_resale_price_trends(context_query)


@mcp.tool(name="query_occupational_wage_insights")
def mcp_query_occupational_wage_insights(context_query: str = "general") -> str:
    """Looks up Singapore's real per-job-title wages (MOM Occupational Wage Survey, 500+ detailed occupations) with year-on-year increment rates, newly created (AI-era) job titles, and 25th-75th percentile ranges."""
    return query_occupational_wage_insights(context_query)

if __name__ == "__main__":
    mcp.run()
