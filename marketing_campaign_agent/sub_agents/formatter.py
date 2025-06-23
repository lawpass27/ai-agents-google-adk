from google.adk.agents import LlmAgent
from ..instructions import FORMATTER_INSTRUCTION

formatter_agent = LlmAgent(
    name="CampaignBriefFormatter",
    model="gemini-2.0-flash",
    instruction=FORMATTER_INSTRUCTION,
    output_key="final_campaign_brief"
)
