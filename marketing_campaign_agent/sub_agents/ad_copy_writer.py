from google.adk.agents import LlmAgent
from ..instructions import AD_COPY_WRITER_INSTRUCTION

ad_copy_writer_agent = LlmAgent(
    name="AdCopyWriter",
    model="gemini-2.0-flash",
    instruction=AD_COPY_WRITER_INSTRUCTION,
    output_key="ad_copy_variations"
)
