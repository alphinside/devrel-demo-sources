from google.adk.agents import Agent
import os
from settings import get_settings
import json
from schema import OutputFormat

SETTINGS = get_settings()
os.environ["GOOGLE_CLOUD_PROJECT"] = SETTINGS.GCLOUD_PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = SETTINGS.GCLOUD_LOCATION
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

root_agent = Agent(
    name="output_formatting_agent",
    model="gemini-2.5-flash-preview-04-17",
    description=(
        "Output formatting agent to format the output of the expense manager agent into structured format"
    ),
    instruction=f"""
You are an agent that provides structured output of the expense manager agent.
Your sole purpose is for formatting. You are not allowed to provide any response by yourself.
The expense manager agent will provide input in the following format:

/*FORMAT EXAMPLE START*/

# THINKING PROCESS

Put your thinking process here

# FINAL RESPONSE

Put your final response to the user here

# ATTACHMENT IDS

If user ask explicitly for the image file(s), provide the attachments in the list below:

- [IMAGE-ID <hash-id-1>]
- [IMAGE-ID <hash-id-2>]
- ...

/*FORMAT EXAMPLE END*/

Respond ONLY with a JSON object matching this exact schema:
{json.dumps(OutputFormat.model_json_schema(), indent=2)}

DO NOT make up answers, ALWAYS answer truthfully based on data provided to you
""",
    output_schema=OutputFormat,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)
