import gradio as gr
import requests
import base64
from pathlib import Path
from typing import List, Dict, Any
from settings import get_settings, DEFAULT_SYSTEM_PROMPT

settings = get_settings()

IMAGE_SUFFIX_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".webp": "image/webp",
}
DOCUMENT_SUFFIX_MIME_MAP = {
    ".pdf": "application/pdf",
}


def get_mime_type(filepath: str) -> str:
    """Get the MIME type for a file based on its extension.

    Args:
        filepath: Path to the file.

    Returns:
        str: The MIME type of the file.

    Raises:
        ValueError: If the file type is not supported.
    """
    filepath = Path(filepath)
    suffix = filepath.suffix

    # modify ".jpg" suffix to ".jpeg" to unify the mime type
    suffix = suffix if suffix != ".jpg" else ".jpeg"

    if suffix in IMAGE_SUFFIX_MIME_MAP:
        return IMAGE_SUFFIX_MIME_MAP[suffix]
    elif suffix in DOCUMENT_SUFFIX_MIME_MAP:
        return DOCUMENT_SUFFIX_MIME_MAP[suffix]
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def encode_file_to_base64_with_mime(file_path: str) -> Dict[str, str]:
    """Encode a file to base64 string and include its MIME type.

    Args:
        file_path: Path to the file to encode.

    Returns:
        Dict[str, str]: Dictionary with 'data' and 'mime_type' keys.
    """
    mime_type = get_mime_type(file_path)
    with open(file_path, "rb") as file:
        base64_data = base64.b64encode(file.read()).decode("utf-8")

    return {"data": base64_data, "mime_type": mime_type}


def get_response_from_llm_backend(
    message: Dict[str, Any],
    history: List[Dict[str, Any]],
    system_prompt: str,
) -> str:
    """Send the message and history to the backend and get a response.

    Args:
        message: Dictionary containing the current message with 'text' and optional 'files' keys.
        history: List of previous message dictionaries in the conversation.
        system_prompt: The system prompt to be sent to the backend.

    Returns:
        str: The text response from the backend service.
    """

    # Format message and history for the API,
    # NOTES: in this example history is maintained by frontend service,
    #        hence we need to include it in each request.
    #        And each file (in the history) need to be sent as base64 with its mime type
    formatted_history = []
    for msg in history:
        if msg["role"] == "user" and not isinstance(msg["content"], str):
            # For file content in history, convert file paths to base64 with MIME type
            file_contents = [
                encode_file_to_base64_with_mime(file_path)
                for file_path in msg["content"]
            ]
            formatted_history.append({"role": msg["role"], "content": file_contents})
        else:
            formatted_history.append({"role": msg["role"], "content": msg["content"]})

    # Extract files and convert to base64 with MIME type
    files_with_mime = []
    if uploaded_files := message.get("files", []):
        for file_path in uploaded_files:
            files_with_mime.append(encode_file_to_base64_with_mime(file_path))

    # Prepare the request payload
    payload = {
        "message": {"text": message["text"], "files": files_with_mime},
        "history": formatted_history,
        "system_prompt": system_prompt,
    }

    # Send request to backend
    try:
        response = requests.post(settings.BACKEND_URL, json=payload)
        response.raise_for_status()  # Raise exception for HTTP errors

        result = response.json()
        if error := result.get("error"):
            return f"Error: {error}"

        return result.get("response", "No response received from backend")
    except requests.exceptions.RequestException as e:
        return f"Error connecting to backend service: {str(e)}"


if __name__ == "__main__":
    demo = gr.ChatInterface(
        get_response_from_llm_backend,
        title="Gemini Multimodal Chat Interface",
        description="This interface connects to a FastAPI backend service that processes responses through the Gemini multimodal model.",
        type="messages",
        multimodal=True,
        textbox=gr.MultimodalTextbox(file_count="multiple"),
        additional_inputs=[
            gr.Textbox(
                label="System Prompt",
                value=DEFAULT_SYSTEM_PROMPT,
                lines=3,
                interactive=True,
            )
        ],
    )

    demo.launch(
        server_name="0.0.0.0",
        server_port=8080,
    )
