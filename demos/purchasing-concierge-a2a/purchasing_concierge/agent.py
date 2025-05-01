from .purchasing_agent import PurchasingAgent
from settings import get_settings
import os

SETTINGS = get_settings()
os.environ["GOOGLE_CLOUD_PROJECT"] = SETTINGS.GCLOUD_PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = SETTINGS.GCLOUD_LOCATION
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

root_agent = PurchasingAgent(
    remote_agent_addresses=["http://localhost:10000"]
).create_agent()
