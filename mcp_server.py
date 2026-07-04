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
    query_singapore_job_statistics_via_bigquery
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
    """Queries Singapore's public job market and employment statistics database using Google BigQuery."""
    return query_singapore_job_statistics_via_bigquery(context_query)

if __name__ == "__main__":
    mcp.run()
