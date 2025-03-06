import json
import os
import vertexai
from vertexai.generative_models import GenerativeModel
from flask import Flask, request, Request
from settings import get_settings
from google.oauth2 import service_account
from llm_guard import scan_output, scan_prompt
from llm_guard.input_scanners import Anonymize, PromptInjection, TokenLimit, Toxicity
from llm_guard.output_scanners import Deanonymize, NoRefusal, Relevance, Sensitive
from llm_guard.vault import Vault

settings = get_settings()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1"
PARENT = f"projects/{PROJECT_ID}"
MODEL_NAME = "gemini-2.0-flash-001"
DEFAULT_PROMPT = """My name is John Doe, I live at 123 Main Street, Anytown, USA.
My credit card number is 4111-2222-3333-4444 and my social security number is 999-88-7777. 
My email is john.doe@example.com and my phone number is 555-123-4567.
I want to learn about the benefits of cloud computing for someone with my background.
What are the privacy and security implications I should be aware of?"""

credentials = service_account.Credentials.from_service_account_file(
    settings.CLOUDRUN_SERVICE_ACCOUNT_KEY,
)
vertexai.init(
    project=settings.VERTEX_PROJECT_ID,
    location=settings.VERTEX_LOCATION,
    credentials=credentials,
)

model = GenerativeModel(MODEL_NAME)
vault = Vault()
input_scanners = [Anonymize(vault), Toxicity(), TokenLimit(), PromptInjection()]
output_scanners = [Deanonymize(vault), NoRefusal(), Relevance(), Sensitive()]


def llm_call(prompt):
    response = model.generate_content(prompt)
    return response.text


def handle_llm_request(request: Request):
    request_json = request.get_json(silent=True)

    if not request_json or "prompt" not in request_json or request_json["prompt"] == "":
        prompt = DEFAULT_PROMPT
    else:
        prompt = request_json.get("prompt")

    #    redacted_prompt = redact_string(prompt, pre_call_findings)
    sanitized_prompt, results_valid, results_score = scan_prompt(input_scanners, prompt)
    llm_response = llm_call(sanitized_prompt)
    sanitized_response_text, results_valid, results_score = scan_output(
        output_scanners, sanitized_prompt, llm_response
    )
    #    redacted_response = redact_string(llm_response, post_call_findings)

    log_data = {
        "original_prompt": prompt,
        "sanitized_prompt": sanitized_prompt,
        "llm_response": llm_response,
        "sanitize_response": sanitized_response_text,
    }

    return log_data, 200


if __name__ == "__main__":
    from pprint import pprint

    app = Flask(__name__)

    with app.test_request_context(
        path="/",
        method="POST",
        data=json.dumps({"prompt": ""}),
        content_type="application/json",
    ):
        response, status_code = handle_llm_request(request)
        pprint(f"Request Response: {response}, Status Code: {status_code}")
