import gradio as gr
import requests
import base64
from typing import List, Dict, Any
from settings import get_settings
from PIL import Image
import io
from schema import ImageData, ChatRequest, ChatResponse


SETTINGS = get_settings()


def encode_image_to_base64(image_path: str) -> ImageData:
    """Encode a file to base64 string.

    Reads an image file and returns the base64-encoded image data.

    Args:
        image_path: Path to the image file to encode.

    Returns:
        ImageData object containing the base64 encoded image data.
    """
    # Read the image file
    with open(image_path, "rb") as file:
        image_content = file.read()

    # Base64 encode the image
    base64_data = base64.b64encode(image_content).decode("utf-8")

    # Return as ImageData object
    return ImageData(serialized_image=base64_data)


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


def get_response_from_llm_backend(
    message: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> List[str | gr.Image]:
    """Send the message and history to the backend and get a response.

    Args:
        message: Dictionary containing the current message with 'text' and optional 'files' keys.
        history: List of previous message dictionaries in the conversation.

    Returns:
        List containing text response and any image attachments from the backend service.
    """
    # Extract files and convert to base64
    image_data = []
    if uploaded_files := message.get("files", []):
        for file_path in uploaded_files:
            image_data.append(encode_image_to_base64(file_path))

    # Prepare the request payload
    payload = ChatRequest(
        text=message["text"],
        files=image_data,
        session_id="default_session",
        user_id="default_user",
    )

    # Send request to backend
    try:
        response = requests.post(SETTINGS.BACKEND_URL, json=payload.model_dump())
        response.raise_for_status()  # Raise exception for HTTP errors

        result = ChatResponse(**response.json())
        if result.error:
            return [f"Error: {result.error}"]

        chat_responses = []

        if result.thinking_process:
            chat_responses.append(
                gr.ChatMessage(
                    role="assistant",
                    content=result.thinking_process,
                    metadata={"title": "🧠 Thinking Process"},
                )
            )

        chat_responses.append(gr.ChatMessage(role="assistant", content=result.response))

        if result.attachments:
            for attachment in result.attachments:
                image_data = attachment.serialized_image
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
