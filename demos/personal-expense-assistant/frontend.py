import gradio as gr
import requests
import base64
import hashlib
from typing import List, Dict, Any
from settings import get_settings
from PIL import Image
import io
from utils import extract_attachment_ids_from_response


SETTINGS = get_settings()


def encode_image_to_base64_with_webp_standardization(image_path: str) -> Dict[str, str]:
    """Encode a file to base64 string and standardize to WebP format.

    Reads an image file, converts it to WebP format for standardization,
    and returns both the base64-encoded image data and a hash ID for reference.

    Args:
        image_path: Path to the image file to encode.

    Returns:
        Dict with 'serialized_image' (base64 string) and 'image_hash_id' (hash string) keys.
    """
    # Read the raw image file
    with open(image_path, "rb") as file:
        image_content = file.read()

    # Convert to standardized WebP format using PIL
    img = Image.open(io.BytesIO(image_content))
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Save as WebP in memory
    webp_buffer = io.BytesIO()
    img.save(webp_buffer, format="WEBP", quality=90)
    webp_buffer.seek(0)
    webp_data = webp_buffer.getvalue()

    # Base64 encode the standardized image
    base64_data = base64.b64encode(webp_data).decode("utf-8")
    image_hash_id = hashlib.sha256(webp_data).hexdigest()[:12]

    return {
        "serialized_image": base64_data,
        "image_hash_id": image_hash_id,
    }


def decode_base64_to_image(base64_data: str) -> Image.Image:
    """Decode a base64 string to PIL Image.

    Converts a base64-encoded image string back to a PIL Image object
    that can be displayed or processed further.

    Args:
        base64_data: Base64 encoded string of the image.

    Returns:
        PIL Image object of the decoded image.
    """
    # Decode the base64 string and convert to PIL Image
    image_data = base64.b64decode(base64_data)
    image_buffer = io.BytesIO(image_data)
    image = Image.open(image_buffer)

    return image


def format_conversation_history(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format the conversation history for API consumption.

    Processes each message in the conversation history to ensure images are
    properly referenced by their hash IDs for efficiency. This handles different
    types of content (text, images) and extracts attachment IDs from assistant responses.

    Args:
        history: List of previous message dictionaries in the conversation.

    Returns:
        Formatted history list ready for API consumption.
    """
    formatted_history = []
    for msg in history:
        # Image uploaded by user will be in tuple
        if isinstance(msg["content"], tuple):
            file_contents = [
                {
                    "image_hash_id": encode_image_to_base64_with_webp_standardization(
                        file_path
                    )["image_hash_id"]
                }
                for file_path in msg["content"]
            ]
            formatted_history.append({"role": msg["role"], "content": file_contents})
        # Image from assistant response will be in gr.Image
        elif isinstance(msg["content"], gr.Image):
            # Image ID from assistant response will be extracted from assistant string response
            # inside <attachments> tag
            pass
        elif isinstance(msg["content"], str):
            formatted_history.append({"role": msg["role"], "content": msg["content"]})

            # Extract Image ID from assistant response
            attachment_ids = extract_attachment_ids_from_response(msg["content"])
            if attachment_ids:
                formatted_history.append(
                    {
                        "role": msg["role"],
                        "content": [
                            {"image_hash_id": attachment_id}
                            for attachment_id in attachment_ids
                        ],
                    }
                )

        else:
            raise ValueError(
                f"Unsupported message content type: {type(msg['content'])}"
            )

    return formatted_history


def get_response_from_llm_backend(
    message: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> List[str | gr.Image]:
    """Send the message and history to the backend and get a response.

    Formats the conversation history and current message (including any attached images),
    sends them to the backend service, and processes the response which may include
    both text and image content.

    Args:
        message: Dictionary containing the current message with 'text' and optional 'files' keys.
        history: List of previous message dictionaries in the conversation.

    Returns:
        List containing text response and any image attachments from the backend service.
    """

    # Format history for the API
    # NOTES: in this example history is maintained by frontend service,
    #        hence we need to include it in each request.
    #        And each image in the history will be replaced with image_hash_id for efficiency
    formatted_history = format_conversation_history(history)

    # Extract files and convert to base64
    image_data_with_mime = []
    if uploaded_files := message.get("files", []):
        for file_path in uploaded_files:
            image_data_with_mime.append(
                encode_image_to_base64_with_webp_standardization(file_path)
            )

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
            return [f"Error: {error}"]

        chat_responses = [result.get("response", "No response received from backend")]

        if result.get("attachments", []):
            for attachment in result["attachments"]:
                image_data = attachment["serialized_image"]
                chat_responses.append(gr.Image(decode_base64_to_image(image_data)))

        return chat_responses
    except requests.exceptions.RequestException as e:
        return [f"Error connecting to backend service: {str(e)}"]


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
