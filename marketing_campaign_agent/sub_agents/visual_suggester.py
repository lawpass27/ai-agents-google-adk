from google.adk.agents import LlmAgent
from ..instructions import VISUAL_SUGGESTER_INSTRUCTION

visual_suggester_agent = LlmAgent(
    name="VisualSuggester",
    model="gemini-2.0-flash",
    instruction=VISUAL_SUGGESTER_INSTRUCTION,
    output_key="visual_concepts"
)
