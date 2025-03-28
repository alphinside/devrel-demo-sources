import base64
from fastapi import FastAPI, Body
from smolagents import LiteLLMModel, CodeAgent
import litellm
from settings import get_settings
from typing import List, Optional, Tuple
from pydantic import BaseModel
from PIL import Image
import io
import hashlib
from agent_tools import store_receipt_data, get_receipt_data_by_image_id

app = FastAPI(title="Personal Expense Assistant Backend Service")

SETTINGS = get_settings()
litellm.vertex_project = SETTINGS.GCLOUD_PROJECT_ID
litellm.vertex_location = SETTINGS.GCLOUD_LOCATION


# System prompt template for the expense processing agent
EXPENSE_ASSISTANT_PROMPT = """
You are a helpful Personal Expense Assistant designed to help users track expenses,
analyze receipts, and manage their financial records. You always 
speak in Bahasa Indonesia.

IMPORTANT INFORMATION ABOUT IMAGES:
- When a user recent message contains images of receipts, 
  it will appear in the conversation as a placeholder like 
  [IMAGE-POSITION 0-ID <hash-id>], [IMAGE-POSITION 1-ID <hash-id>], etc.
- However if receipt images are provided in the conversation history, 
  it will appear in the conversation as a placeholder in the format of
  [IMAGE-ID <hash-id>], as the image data will not be provided directly to you.
  You will need to use tool to fetch the receipt content using the hash-id.
- These placeholders correspond to images in an array (that is not visible to the user) that you can analyze.
- Image data placeholder [IMAGE-POSITION 0-ID <hash-id>] refers to the first image (index 0) in the images data provided.
  where <hash-id> is the unique identifier of the image.
- When user refers to an image by position, it refer to the appearance of image in the conversation history which might
  different from the position of image in the images data provided. If you are not sure about this, always ask verification
  to the user.

When analyzing receipt images, extract and organize the following information 
when available:
1. Store/Merchant name
2. Date of purchase
3. Total amount spent
4. Individual items purchased with their prices
5. Payment method used
6. Any discounts or taxes applied

Key capabilities:
- Store receipt data for future reference
- Find and retrieve previously stored receipts by date, merchant, or amount
- Calculate and track spending over time periods (daily, weekly, monthly)
- Categorize expenses (food, transportation, entertainment, etc.)
- Identify spending patterns and provide insights

If the user asks questions about their spending or receipts but 
hasn't provided the necessary information yet, politely ask for 
clarification or request they upload relevant receipt images.

If previous receipt image (identified by hash-id) is already stored, DO NOT store again.

NEVER expose the receipt image hash id to the user.

Always be helpful, concise, and focus on providing accurate 
financial information based on the receipts provided.

Conversation history so far:

{history}

Recent user message:

{recent_message}

Now take appropriate action and respond to the user
"""


class ImageData(BaseModel):
    """Model for a file with base64 data and MIME type.

    Attributes:
        serialized_image: Base64 encoded string of the image content.
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
    error: Optional[str] = None


def _process_image_data(
    serialized_image: str, position: int = None
) -> Tuple[str, Image.Image | None]:
    """Process image data and return placeholder and optionally the PIL image.

    Args:
        serialized_image: Base64 encoded image data
        position: Position index for the image, if provided uses IMAGE-POSITION format

    Returns:
        Tuple containing:
            - Image placeholder string
            - PIL Image object, if position is provided else None
    """
    image_data = base64.b64decode(serialized_image)
    image_hash = hashlib.sha256(image_data).hexdigest()[:12]

    # Create the appropriate placeholder based on whether position is provided
    pil_image = None
    if position is not None:
        placeholder = f"[IMAGE-POSITION {position}-ID {image_hash}]"
        pil_image = Image.open(io.BytesIO(image_data))
    else:
        placeholder = f"[IMAGE-ID {image_hash}]"

    return placeholder, pil_image


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
                placeholder, _ = _process_image_data(data.serialized_image)
                formatted_history += f"{role.title()}: {placeholder}\n"
        else:
            formatted_history += f"{role.title()}: {content}\n"

    return formatted_history


def reformat_recent_message(message: LastUserMessage) -> Tuple[str, List[Image.Image]]:
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
        placeholder, img = _process_image_data(
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
            tools=[store_receipt_data, get_receipt_data_by_image_id], model=model
        )

        # Reformat chat history and extract images
        formatted_history = reformat_chat_history(request.chat_history)

        # Reformat recent message and extract images
        formatted_recent_message, recent_images = reformat_recent_message(
            request.recent_message
        )

        # Generate response
        result = agent.run(
            EXPENSE_ASSISTANT_PROMPT.format(
                history=formatted_history, recent_message=formatted_recent_message
            ),
            images=recent_images,
        )

        print(f"Generated response: {result}")

        return ChatResponse(response=result)
    except Exception as e:
        print(f"Error in processing: {str(e)}")
        return ChatResponse(
            response="", error=f"Error in generating response: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
