import gradio as gr
import requests
import base64
from typing import List, Dict, Any
from settings import get_settings

settings = get_settings()


def encode_image_to_base64(image_path: str) -> Dict[str, str]:
    """Encode a file to base64 string.

    Args:
        image_path: Path to the image file to encode.

    Returns:
        Dict[str, str]: Dictionary with 'serialized_image' key.
    """
    with open(image_path, "rb") as file:
        base64_data = base64.b64encode(file.read()).decode("utf-8")

    return {"serialized_image": base64_data}


def get_response_from_llm_backend(
    message: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> str:
    """Send the message and history to the backend and get a response.

    Args:
        message: Dictionary containing the current message with 'text' and optional 'files' keys.
        history: List of previous message dictionaries in the conversation.

    Returns:
        str: The text response from the backend service.
    """

    # Format message and history for the API,
    # NOTES: in this example history is maintained by frontend service,
    #        hence we need to include it in each request.
    #        And each image (in the history) need to be sent as base64
    formatted_history = []
    for msg in history:
        if msg["role"] == "user" and not isinstance(msg["content"], str):
            # For file content in history, convert file paths to base64 with MIME type
            file_contents = [
                encode_image_to_base64(file_path) for file_path in msg["content"]
            ]
            formatted_history.append({"role": msg["role"], "content": file_contents})
        else:
            formatted_history.append({"role": msg["role"], "content": msg["content"]})

    # Extract files and convert to base64
    images_file = []
    if uploaded_files := message.get("files", []):
        for file_path in uploaded_files:
            images_file.append(encode_image_to_base64(file_path))

        formatted_history.append({"role": "user", "content": images_file})

    if message["text"]:
        formatted_history.append({"role": "user", "content": message["text"]})

    # Prepare the request payload
    payload = {
        "chat_history": formatted_history,
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
        title="Personal Expense Assistant",
        description="This assistant can help you to store receipts data, find receipts, and track your expenses during certain period.",
        type="messages",
        multimodal=True,
        textbox=gr.MultimodalTextbox(file_count="multiple", file_types=["image"]),
    )

    demo.launch(
        server_name="0.0.0.0",
        server_port=8080,
    )
