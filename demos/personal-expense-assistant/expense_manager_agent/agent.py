from google.adk.agents import Agent
from expense_manager_agent.tools import store_receipt_data, search_receipts_by_metadata_filter, search_relevant_receipts_by_natural_language_query,get_receipt_data_by_image_id
import os
from settings import get_settings
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest

SETTINGS = get_settings()
os.environ["GOOGLE_CLOUD_PROJECT"] = SETTINGS.GCLOUD_PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = SETTINGS.GCLOUD_LOCATION  
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

# Get the code file directory path and read the task prompt file
current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_path = os.path.join(current_dir, "task_prompt.md")
with open(prompt_path, "r") as file:
    task_prompt = file.read()

def modify_image_data_to_string_placeholder_in_history(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    # TODO: Implement image data modification to string placeholder in history
    pass

root_agent = Agent(
    name="expense_manager_agent",
    model="gemini-2.5-flash-preview-04-17",
    description=(
        "Personal expense agent to help user track expenses, analyze receipts, and manage their financial records"
    ),
    instruction=task_prompt,
    tools=[store_receipt_data, get_receipt_data_by_image_id,search_receipts_by_metadata_filter, search_relevant_receipts_by_natural_language_query],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    before_model_callback=modify_image_data_to_string_placeholder_in_history
) 