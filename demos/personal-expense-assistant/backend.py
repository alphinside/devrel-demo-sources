import base64
from fastapi import FastAPI, Body
from smolagents import LiteLLMModel, CodeAgent
import litellm
from settings import get_settings
from typing import List, Optional, Tuple
from pydantic import BaseModel
from PIL import Image
import io
from agent_tools import store_receipt_data
import uuid

app = FastAPI(title="Personal Expense Assistant Backend Service")

settings = get_settings()
litellm.vertex_project = settings.VERTEXAI_PROJECT_ID
litellm.vertex_location = settings.VERTEXAI_LOCATION


# System prompt template for the expense processing agent
EXPENSE_PROCESSING_PROMPT = """
You are a Personal Expense Assistant designed to help users track expenses,
analyze receipts, and manage their financial records.

IMPORTANT INFORMATION ABOUT IMAGES:
- When a user sends an image of a receipt, 
  it will appear in the conversation as a placeholder like 
  [IMAGE-POSITION 0-ID <uuid>], [IMAGE-POSITION 1-ID <uuid>], etc.
- These placeholders correspond to images in an array that you can analyze.
- For example, [IMAGE-POSITION 0-ID <uuid>] refers to the first image (index 0) in the images array.
  where <uuid> is the unique identifier of the image.

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

Always be helpful, concise, and focus on providing accurate 
financial information based on the receipts provided.

Conversation history so far:

{history}
Now take approriate action and respond to the user
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
    """

    chat_history: List[Message]


class ChatResponse(BaseModel):
    """Model for a chat response.

    Attributes:
        response: The text response from the model.
        error: Optional error message if something went wrong.
    """

    response: str
    error: Optional[str] = None


def reformat_chat_history(history: List[Message]) -> Tuple[str, List[Image.Image]]:
    """Reformats chat history into a specific string format and extracts images.

    Args:
        history: List of chat messages with role and content.

    Returns:
        Tuple containing:
            - Formatted chat history as a string
            - List of PIL Image objects extracted from the history
    """
    formatted_history = ""
    images = []

    for msg in history:
        role = msg.role
        content = msg.content

        if role == "user":
            # Check if content is a list (contains files/images)
            if isinstance(content, list):
                for item in content:
                    # This is an image
                    image_id = str(uuid.uuid4())
                    image_position = f"[IMAGE-POSITION {len(images)}-ID {image_id}]"

                    # Convert base64 to PIL Image
                    image_data = base64.b64decode(item.serialized_image)
                    img = Image.open(io.BytesIO(image_data))
                    images.append(img)

                    # TODO: Store image in database or storage with relevant ID

                    formatted_history += f"User: {image_position}\n"
            else:
                # Simple text message
                formatted_history += f"User: {content}\n"
        elif role == "assistant":
            formatted_history += f"Assistant: {content}\n"

    return formatted_history, images


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
        agent = CodeAgent(tools=[store_receipt_data], model=model)

        # Reformat chat history and extract images
        formatted_history, images = reformat_chat_history(request.chat_history)

        # Generate response
        result = agent.run(
            EXPENSE_PROCESSING_PROMPT.format(history=formatted_history),
            images=images,
        )

        print(f"Generated response: {result}")

        return ChatResponse(response=result)
    except Exception as e:
        return ChatResponse(
            response="", error=f"Error in generating response: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
