from google.adk.agents import SequentialAgent
from .instructions import CAMPAIGN_ORCHESTRATOR_INSTRUCTION
from .sub_agents import (
    market_research_agent,
    messaging_strategist_agent,
    ad_copy_writer_agent,
    visual_suggester_agent,
    formatter_agent,
)

campaign_orchestrator = SequentialAgent(
    name="MarketingCampaignAssistant",
    description=CAMPAIGN_ORCHESTRATOR_INSTRUCTION,
    sub_agents=[
        market_research_agent,
        messaging_strategist_agent,
        ad_copy_writer_agent,
        visual_suggester_agent,
        formatter_agent,
    ],
)

root_agent = campaign_orchestrator
