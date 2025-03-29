import gradio as gr
import requests
import base64
from typing import List, Dict, Any
from settings import get_settings
from PIL import Image
import io

SETTINGS = get_settings()


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


def decode_base64_to_image(base64_data: str) -> Image:
    """Decode a base64 string to a PIL Image.

    Args:
        base64_data: Base64 encoded string of the image.

    Returns:
        PIL.Image.Image: Decoded image.
    """

    # Decode the base64 string and convert to PIL Image
    image_data = base64.b64decode(base64_data)
    image_buffer = io.BytesIO(image_data)
    image = Image.open(image_buffer)

    return image


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
        if isinstance(msg["content"], tuple):
            # For file content in history, convert file paths to base64 with MIME type
            file_contents = [
                encode_image_to_base64(file_path) for file_path in msg["content"]
            ]
            formatted_history.append({"role": msg["role"], "content": file_contents})
        elif isinstance(msg["content"], str):
            formatted_history.append({"role": msg["role"], "content": msg["content"]})
        elif isinstance(msg["content"], gr.Image):
            # Skip image content in history which provided by assistant response
            pass
        else:
            raise ValueError(
                f"Unsupported message content type: {type(msg['content'])}"
            )

    # Extract files and convert to base64
    image_data_with_mime = []
    if uploaded_files := message.get("files", []):
        for file_path in uploaded_files:
            image_data_with_mime.append(encode_image_to_base64(file_path))

    # Prepare the request payload
    payload = {
        "chat_history": formatted_history,
        "recent_message": {
            "text": message["text"],
            "files": image_data_with_mime,
        },
    }

    # Send request to backend
    try:
        response = requests.post(SETTINGS.BACKEND_URL, json=payload)
        response.raise_for_status()  # Raise exception for HTTP errors

        result = response.json()
        if error := result.get("error"):
            return f"Error: {error}"

        chat_responses = [result.get("response", "No response received from backend")]

        if result.get("attachments", []):
            for attachment in result["attachments"]:
                chat_responses.append(gr.Image(decode_base64_to_image(attachment)))

        return chat_responses
    except requests.exceptions.RequestException as e:
        return f"Error connecting to backend service: {str(e)}"


if __name__ == "__main__":
    demo = gr.ChatInterface(
        get_response_from_llm_backend,
        title="Personal Expense Assistant",
        description="This assistant can help you to store receipts data, find receipts, and track your expenses during certain period.",
        type="messages",
        multimodal=True,
        textbox=gr.MultimodalTextbox(file_types=["image"]),
    )

    demo.launch(
        server_name="0.0.0.0",
        server_port=8080,
    )
