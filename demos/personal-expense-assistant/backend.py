import base64
from typing import List, Optional, Tuple
from fastapi import FastAPI, Body
from pydantic import BaseModel
import io
from PIL import Image
import os
from settings import get_settings
from agent_tools import (
    store_receipt_data,
    get_receipt_data_by_image_id,
    search_receipts_by_metadata_filter,
    search_relevant_receipts_by_natural_language_query,
)
from utils import (
    store_image_in_gcs,
    download_image_from_gcs,
    extract_attachment_ids_from_response,
)
from smolagents import LiteLLMModel, CodeAgent
import litellm

app = FastAPI(title="Personal Expense Assistant Backend Service")

SETTINGS = get_settings()
litellm.vertex_project = SETTINGS.GCLOUD_PROJECT_ID
litellm.vertex_location = SETTINGS.GCLOUD_LOCATION


class ImageData(BaseModel):
    """Model for image data with hash identifier.

    Attributes:
        image_hash_id: Hash identifier of the image.
        serialized_image: Optional Base64 encoded string of the image content.
    """

    image_hash_id: str
    serialized_image: str | None = None


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
        files: List of image data objects containing image information.
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
        attachments: List of image data to be displayed to the user.
        error: Optional error message if something went wrong.
    """

    response: str
    attachments: List[ImageData] = []
    error: Optional[str] = None


def process_image_data(
    serialized_image: str, image_hash_id: str, position: int
) -> Tuple[str, Image.Image]:
    """Process image data and return placeholder and the PIL image.

    Decodes base64 image data, stores it in cloud storage, and creates a placeholder
    string for the conversation history.

    Args:
        serialized_image: Base64 encoded image data.
        image_hash_id: Hash identifier of the image.
        position: Position index for the image in the current message.

    Returns:
        Tuple containing:
            - Image placeholder string formatted as [IMAGE-POSITION {position}-ID {image_hash_id}].
            - PIL Image object of the decoded image.
    """
    image_data = base64.b64decode(serialized_image)

    # Store in Google Cloud Storage
    store_image_in_gcs(image_data, image_hash_id)

    # Create the image data string placeholder
    placeholder = f"[IMAGE-POSITION {position}-ID {image_hash_id}]"
    pil_image = Image.open(io.BytesIO(image_data))

    return placeholder, pil_image


def reformat_image_hash_id_to_placeholder(image_hash_id: str) -> str:
    """Create a placeholder string with image ID and parsed data.

    Retrieves parsed data for an image from the database using its hash identifier,
    then returns a placeholder string containing the image ID and parsed data.

    Args:
        image_hash_id: Hash identifier of the image.

    Returns:
        str: A formatted placeholder string containing the image ID and parsed data
             in the format "[IMAGE-ID {hash_id}]\n{parsed_data}".
    """
    image_parsed_data = get_receipt_data_by_image_id(image_hash_id)
    placeholder = f"[IMAGE-ID {image_hash_id}]\n{image_parsed_data}"
    return placeholder


def reformat_chat_history(history: List[Message]) -> str:
    """Reformat chat history into a specific string format.

    Converts the structured chat history into a plain text format for the LLM.
    Image data in chat history will be replaced with placeholders that include
    the parsed receipt data.

    Example result after reformatting:

    User: Hello, I need help with my expenses
    Assistant: I'd be happy to help with your expenses. You can upload receipts or ask questions.
    User: [IMAGE-ID some-hash-id-here]
    {parsed_receipt_data}
    User: please process and store this receipt

    Args:
        history: List of chat messages with role and content.

    Returns:
        str: Formatted chat history as a string for LLM processing.
    """
    formatted_history = ""

    for msg in history:
        role = msg.role
        content = msg.content

        if isinstance(content, list):
            for data in content:
                # Process this image without returning image data
                placeholder = reformat_image_hash_id_to_placeholder(data.image_hash_id)
                formatted_history += f"{role.title()}: {placeholder}\n"
        else:
            formatted_history += f"{role.title()}: {content}\n"

    return formatted_history


def reformat_recent_message_and_process_images(
    message: LastUserMessage,
) -> Tuple[str, List[Image.Image]]:
    """Reformat the recent user message and process any included images.

    Similar to reformat_chat_history but for a LastUserMessage object. For the recent
    message, the image data is available and will be processed, stored, and converted
    to placeholder strings with position information.

    Example result after reformatting:

    User: [IMAGE-POSITION 0-ID some-hash-id-here]
    User: Hello, I need help with my expenses

    Args:
        message: The most recent user message with text and possibly image files.

    Returns:
        Tuple containing:
            - Formatted message as a string for LLM processing.
            - List of PIL Image objects extracted from the message for visual processing.
    """
    formatted_message = ""
    images = []

    # Handle image files if present
    for data in message.files:
        # Process the image and convert to string placeholder
        placeholder, img = process_image_data(
            data.serialized_image, data.image_hash_id, position=len(images)
        )

        # Add image to the list
        if img:
            images.append(img)

        formatted_message += f"User: {placeholder}\n"

    # Handle text content if present
    if message.text:
        formatted_message += f"User: {message.text}\n"

    return formatted_message, images


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest = Body(...),
) -> ChatResponse:
    """Process a chat request and return a response from the language model.

    This endpoint handles the core chat functionality, processing user messages and images,
    formatting them for the LLM, running the conversation agent, and extracting any
    attachments from the response.

    Args:
        request: The chat request containing message history and the recent message.

    Returns:
        ChatResponse: The model's response containing text and optional attachments.
    """
    try:
        # Log the request
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
            planning_interval=5,
            additional_authorized_imports=["json"],
        )

        # Currently, system prompt modification is not really straightforward
        agent.prompt_templates["system_prompt"] = (
            agent.prompt_templates["system_prompt"]
            + "\nDO NOT generate code block starts with ```tool_code, always use ```py"
            + "\nDO NOT use `*args` or `**kwargs` as function arguments"
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
            max_steps=10,
        )

        # Extract and process any attachments in the response
        base64_attachments = []
        attachment_ids = extract_attachment_ids_from_response(result)

        # Download images from GCS and replace hash IDs with base64 data
        for image_hash_id in attachment_ids:
            base64_data = download_image_from_gcs(image_hash_id)
            if base64_data:
                base64_attachments.append(
                    ImageData(serialized_image=base64_data, image_hash_id=image_hash_id)
                )

        return ChatResponse(response=result, attachments=base64_attachments)
    except Exception as e:
        print(f"Error in processing: {str(e)}")
        return ChatResponse(
            response="", error=f"Error in generating response: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
