import base64
import json
from fastapi import FastAPI, Body
from smolagents import LiteLLMModel, CodeAgent
import litellm
from PIL import Image
import io
import hashlib
import os
from settings import get_settings
from typing import List, Optional, Tuple
from pydantic import BaseModel
from agent_tools import (
    store_receipt_data,
    get_receipt_data_by_image_id,
    search_receipts_by_metadata_filter,
    search_relevant_receipts_by_natural_language_query,
)
from utils import store_image_in_gcs, download_image_from_gcs

app = FastAPI(title="Personal Expense Assistant Backend Service")

SETTINGS = get_settings()
litellm.vertex_project = SETTINGS.GCLOUD_PROJECT_ID
litellm.vertex_location = SETTINGS.GCLOUD_LOCATION


class ImageData(BaseModel):
    """Model for a file with base64 data and filename.

    Attributes:
        serialized_image: Base64 encoded string of the image content.
        filename: Optional filename of the image.
    """

    serialized_image: str


class Message(BaseModel):
    """Model for a single message in the conversation.

    Attributes:
        role: The role of the message sender, either 'user' or 'assistant'.
        content: The text content of the message or a list of image data objects.
    """

    role: str
    content: str | List[ImageData]


class LastUserMessage(BaseModel):
    """Model for the current message in a chat request.

    Attributes:
        text: The text content of the message.
        files: List of image data objects containing base64 data.
    """

    text: str
    files: List[ImageData] = []


class ChatRequest(BaseModel):
    """Model for a chat request.

    Attributes:
        chat_history: List of messages in the conversation.
        recent_message: The last message sent by the user.
    """

    chat_history: List[Message]
    recent_message: LastUserMessage


class ChatResponse(BaseModel):
    """Model for a chat response.

    Attributes:
        response: The text response from the model.
        error: Optional error message if something went wrong.
    """

    response: str
    attachments: list[str] = []
    error: Optional[str] = None


def process_image_data(serialized_image: str, position: int) -> Tuple[str, Image.Image]:
    """Process image data and return placeholder and optionally the PIL image.
    Also in case of position is provided, the image will be processed and
    stored in the storage.

    Args:
        serialized_image: Base64 encoded image data
        position: Position index for the image, if provided uses IMAGE-POSITION format

    Returns:
        Tuple containing:
            - Image placeholder string
            - PIL Image object, if position is provided else None
    """
    image_data = base64.b64decode(serialized_image)

    # Convert image to JPEG format using PIL
    img = Image.open(io.BytesIO(image_data))
    if img.mode != "RGB":
        img = img.convert("RGB")
    jpeg_buffer = io.BytesIO()
    img.save(jpeg_buffer, format="JPEG")
    jpeg_data = jpeg_buffer.getvalue()

    # Image hash built from standardization of every image into JPEG format
    image_hash = hashlib.sha256(jpeg_data).hexdigest()[:12]

    # Store in Google Cloud Storage
    store_image_in_gcs(jpeg_data, image_hash)

    # Create the image data string placeholder
    placeholder = f"[IMAGE-POSITION {position}-ID {image_hash}]"
    pil_image = Image.open(io.BytesIO(jpeg_data))

    return placeholder, pil_image


def substitute_image_with_parsed_data(serialized_image: str) -> str:
    """Retrieves parsed data for an image from the database using its hash identifier.
    Then returns a placeholder string containing the image ID and parsed data.

    Args:
        serialized_image: Base64 encoded image data

    Returns:
        str: A formatted placeholder string containing the image ID and parsed data
             in the format "[IMAGE-ID {hash}]\n{parsed_data}"
    """
    image_data = base64.b64decode(serialized_image)
    image_hash = hashlib.sha256(image_data).hexdigest()[:12]

    image_parsed_data = get_receipt_data_by_image_id(image_hash)
    placeholder = f"[IMAGE-ID {image_hash}]\n{image_parsed_data}"
    return placeholder


def reformat_chat_history(history: List[Message]) -> str:
    """Reformats chat history into a specific string format and extracts images.
    Image data in chat history will not be provided again for efficiency.

    Example result after reformatting:

    User: Hello, I need help with my expenses
    Assistant: I'd be happy to help with your expenses. You can upload receipts or ask questions.
    User: [IMAGE-ID some-hash-id-here]
    User: please process and store this receipt

    Args:
        history: List of chat messages with role and content.

    Returns:
        str: Formatted chat history as a string
    """
    formatted_history = ""

    for msg in history:
        role = msg.role
        content = msg.content

        if isinstance(content, list):
            for data in content:
                # Process this image without returning image data
                placeholder = substitute_image_with_parsed_data(data.serialized_image)
                formatted_history += f"{role.title()}: {placeholder}\n"
        else:
            formatted_history += f"{role.title()}: {content}\n"

    return formatted_history


def reformat_recent_message_and_process_images(
    message: LastUserMessage,
) -> Tuple[str, List[Image.Image]]:
    """Reformats a single user message into a specific string format and extracts images.
    Similar to reformat_chat_history but for a LastUserMessage object. Additionally image
    data will be provided in this part hence the image placeholder will contain the image
    data position in the list.

    Example result after reformatting:

    User: [IMAGE-POSITION 0-ID some-hash-id-here]
    User: Hello, I need help with my expenses

    Args:
        message: The most recent user message

    Returns:
        Tuple containing:
            - Formatted message as a string
            - List of PIL Image objects extracted from the message
    """
    formatted_message = ""
    images = []

    # Handle image files if present
    for data in message.files:
        # Process this image and get the image data
        placeholder, img = process_image_data(
            data.serialized_image, position=len(images)
        )

        # Add image to the list
        if img:
            images.append(img)

        formatted_message += f"User: {placeholder}\n"

    # Handle text content if present
    if message.text:
        formatted_message += f"User: {message.text}\n"

    return formatted_message, images


def load_prompt_template() -> str:
    """
    Load the prompt template from task_prompt.md

    Returns:
        str: The prompt template string
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, "task_prompt.md")

    with open(prompt_path, "r") as file:
        return file.read()


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest = Body(...),
) -> ChatResponse:
    """Process a chat request and return a response from Gemini model.

    Args:
        request: The chat request containing message and history.

    Returns:
        ChatResponse: The model's response to the chat request.
    """
    try:
        # Convert message history to Gemini `history` format
        print(f"Received request: {request}")

        # Initialize the model and agent
        model = LiteLLMModel(model_id="vertex_ai/gemini-2.0-flash-001", temperature=0)
        agent = CodeAgent(
            tools=[
                store_receipt_data,
                search_receipts_by_metadata_filter,
                search_relevant_receipts_by_natural_language_query,
            ],
            model=model,
            additional_authorized_imports=["json"],
        )

        # Reformat chat history and replace image data with string placeholder
        formatted_history = reformat_chat_history(request.chat_history)
        formatted_recent_message, recent_images = (
            reformat_recent_message_and_process_images(request.recent_message)
        )

        # Generate response
        prompt_template = load_prompt_template()
        result = agent.run(
            prompt_template.format(
                history=formatted_history, recent_message=formatted_recent_message
            ),
            images=recent_images,
        )

        formatted_result = (
            json.loads(result) if not isinstance(result, dict) else result
        )
        response = ChatResponse(**formatted_result)

        if response.attachments:
            # Download images from GCS and replace hash IDs with base64 data
            base64_attachments = []
            for image_hash_id in response.attachments:
                base64_data = download_image_from_gcs(image_hash_id)
                if base64_data:
                    base64_attachments.append(base64_data)

            # Replace attachments with base64 data
            response.attachments = base64_attachments

        return response
    except Exception as e:
        print(f"Error in processing: {str(e)}")
        return ChatResponse(
            response="", error=f"Error in generating response: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
