import base64
from fastapi import FastAPI, Body
from google.genai.types import Content, Part
from google.genai import Client
from settings import get_settings
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI(title="Gemini Multimodal Service")

settings = get_settings()
GENAI_CLIENT = Client(
    location=settings.VERTEXAI_LOCATION,
    project=settings.VERTEXAI_PROJECT_ID,
    vertexai=True,
)
GEMINI_MODEL_NAME = "gemini-2.0-flash-001"
DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant and ALWAYS relate to this identity. 
You are expert at analyzing given documents or images.
"""


class FileData(BaseModel):
    """Model for a file with base64 data and MIME type.

    Attributes:
        data: Base64 encoded string of the file content.
        mime_type: The MIME type of the file.
    """

    data: str
    mime_type: str


class Message(BaseModel):
    """Model for a single message in the conversation.

    Attributes:
        role: The role of the message sender, either 'user' or 'assistant'.
        content: The text content of the message or a list of file data objects.
    """

    role: str
    content: str | List[FileData]


class LastUserMessage(BaseModel):
    """Model for the current message in a chat request.

    Attributes:
        text: The text content of the message.
        files: List of file data objects containing base64 data and MIME type.
    """

    text: str
    files: List[FileData] = []


class ChatRequest(BaseModel):
    """Model for a chat request.

    Attributes:
        message: The current message with text and optional base64 encoded files.
        history: List of previous messages in the conversation.
        system_prompt: Optional system prompt to be used in the chat.
    """

    message: LastUserMessage
    history: List[Message]
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class ChatResponse(BaseModel):
    """Model for a chat response.

    Attributes:
        response: The text response from the model.
        error: Optional error message if something went wrong.
    """

    response: str
    error: Optional[str] = None


def handle_multimodal_data(file_data: FileData) -> Part:
    """Converts Multimodal data to a Google Gemini Part object.

    Args:
        file_data: FileData object with base64 data and MIME type.

    Returns:
        Part: A Google Gemini Part object containing the file data.
    """
    data = base64.b64decode(file_data.data)  # decode base64 string to bytes
    return Part.from_bytes(data=data, mime_type=file_data.mime_type)


def format_message_history_to_gemini_standard(
    message_history: List[Message],
) -> List[Content]:
    """Converts message history format to Google Gemini Content format.

    Args:
        message_history: List of message objects from the chat history.
            Each message contains 'role' and 'content' attributes.

    Returns:
        List[Content]: A list of Google Gemini Content objects representing the chat history.

    Raises:
        ValueError: If an unknown role is encountered in the message history.
    """
    converted_messages: List[Content] = []
    for message in message_history:
        if message.role == "assistant":
            converted_messages.append(
                Content(role="model", parts=[Part.from_text(text=message.content)])
            )
        elif message.role == "user":
            # Text-only messages
            if isinstance(message.content, str):
                converted_messages.append(
                    Content(role="user", parts=[Part.from_text(text=message.content)])
                )

            # Messages with files
            elif isinstance(message.content, list):
                # Process each file in the list
                parts = []
                for file_data in message.content:
                    if (
                        isinstance(file_data, dict)
                        and "data" in file_data
                        and "mime_type" in file_data
                    ):
                        file_obj = FileData(**file_data)
                        parts.append(handle_multimodal_data(file_obj))

                # Add the parts to a Content object
                if parts:
                    converted_messages.append(Content(role="user", parts=parts))

            else:
                raise ValueError(f"Unexpected content format: {type(message.content)}")

        else:
            raise ValueError(f"Unknown role: {message.role}")

    return converted_messages


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
        converted_messages = format_message_history_to_gemini_standard(request.history)

        # Create chat model
        chat_model = GENAI_CLIENT.chats.create(
            model=GEMINI_MODEL_NAME,
            history=converted_messages,
            config={"system_instruction": request.system_prompt},
        )

        # Prepare multimodal content
        content_parts = []

        # Handle any base64 encoded files in the current message
        if request.message.files:
            for file_data in request.message.files:
                content_parts.append(handle_multimodal_data(file_data))

        # Add text content
        content_parts.append(Part.from_text(text=request.message.text))

        # Send message to Gemini
        response = chat_model.send_message(content_parts)
        print(f"Generated response: {response}")

        return ChatResponse(response=response.text)
    except Exception as e:
        return ChatResponse(
            response="", error=f"Error in generating response: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
