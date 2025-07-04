import os

from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import google_search

linkedInModel = LiteLlm(model=os.environ.get("OPENAI_MODEL"))
instagramModel = LiteLlm(model=os.environ.get("CLAUDE_MODEL"))

print("Google GenAI Model:", os.environ.get("GOOGLE_GENAI_MODEL"))
print("Google GenAI Use VertexAI:", os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"))
print("OpenAI Model:", os.environ.get("OPENAI_MODEL"))
print("Claude Model:", os.environ.get("CLAUDE_MODEL"))
print("OPENAI_API_KEY:", os.environ.get("OPENAI_API_KEY"))
print("GOOGLE_API_KEY:", os.environ.get("GOOGLE_API_KEY"))
print("ANTHROPIC_API_KEY:", os.environ.get("ANTHROPIC_API_KEY"))

researchAgent = Agent(
    name="ResearchAgent",
    model=os.environ.get("GOOGLE_GENAI_MODEL"),
    tools=[google_search],
    description="An agent that researches on the given topic and provides relevant information to other agents for generating social media posts",
    instruction="""
    You are a research assistant. You will be given a topic and you will research on it. Then you will provide a summary of the research.
    """,
    output_key="research_summary",
)

linkedInAgent = Agent(
    model=linkedInModel,
    name="LinkedInPostsAgent",
    description="An agent that generates LinkedIn posts",
    instruction="""
    You are a LinkedIn post generator. You will be given a topic with researched summary from "research_summary" output, and you will generate a LinkedIn post about it.
        The post should be professional, engaging, and relevant to the topic.
        The post should have a primary hook, not more than 60 characters.
        The post should have a line break after the hook.
        The post should have a post-hook that is either supporting the hook or completely inverse of the hook to grab attention.

        The post should be in a conversational tone and should be easy to read.
        There should be bullet points in the post to make it easy to read.
        There should be actionable items in the post to make it easy to follow.

        At the end of the post, there should be a question to engage the audience.
        Finally, ask the audience to share their thoughts in the comments. And to repost.
        Use emojis to make the post more engaging.
        Use hashtags to make the post more discoverable.
    """,
    output_key="linkedIn_post",
)

instagramAgent = Agent(
    model=instagramModel,
    name="InstagramReelScriptAgent",
    description="An agent that generates Instagram reel scripts",
    instruction="""
    You are an Instagram reel script generator. You will be given a topic with researched summary from "research_summary" output, and you will generate a script for an Instagram reel about it.
    The script should be engaging, fast paced, and relevant to the topic.
    The script should have a primary hook, which grabs the attention of the audience.
    The script should have a call to action at the end.
    """,
    output_key="instagram_reel_script",
)

postsAgent = ParallelAgent(
    sub_agents=[linkedInAgent, instagramAgent],
    description="An agent that generates social media posts by using the linkedIn and Instagram agents",
    name="PostsAgent",
)

postsMergerAgent = Agent(
    model=os.environ.get("GOOGLE_GENAI_MODEL"),
    name="PostsMergerAgent",
    description="An agent that merges the posts from the linkedIn and Instagram agents",
    instruction="""
        You are an AI Assistant responsible for combining linkedin and instagram reels script into a structured output.

Your primary task is to merge the posts generated by the LinkedIn and Instagram agents into a single output. Clearly mentioning the platform for each post.
        Input Summaries:
        - LinkedIn Post: {linkedIn_post}
        - Instagram Reels Script: {instagram_reel_script}

        Output Format:
        - LinkedIn Post: {linkedIn_post}
        - Instagram Post: {instagram_reel_script}
""",
)

root_agent = SequentialAgent(
    name="SocialMediaAgent",
    description="An agent that generates social media posts by using the research agent and the posts agent",
    sub_agents=[researchAgent, postsAgent, postsMergerAgent],
)
