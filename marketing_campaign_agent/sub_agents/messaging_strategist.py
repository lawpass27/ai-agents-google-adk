from google.adk.agents import LlmAgent
from ..instructions import MESSAGING_STRATEGIST_INSTRUCTION

messaging_strategist_agent = LlmAgent(
    name="MessagingStrategist",
    model="gemini-2.0-flash",
    instruction=MESSAGING_STRATEGIST_INSTRUCTION,
    output_key="key_messaging"
)
