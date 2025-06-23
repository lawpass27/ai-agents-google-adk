from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from ..instructions import MARKET_RESEARCH_INSTRUCTION

market_research_agent = LlmAgent(
    name="MarketResearcher",
    model="gemini-2.0-flash",
    instruction=MARKET_RESEARCH_INSTRUCTION,
    tools=[google_search],
    output_key="market_research_summary"
)
