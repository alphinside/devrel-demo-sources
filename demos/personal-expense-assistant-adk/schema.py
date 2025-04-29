from pydantic import BaseModel, Field
from typing import List, Optional


class ImageData(BaseModel):
    """Model for image data with hash identifier.

    Attributes:
        serialized_image: Optional Base64 encoded string of the image content.
        mime_type: MIME type of the image.
    """

    serialized_image: str
    mime_type: str


class ChatRequest(BaseModel):
    """Model for a chat request.

    Attributes:
        text: The text content of the message.
        files: List of image data objects
        session_id: Session identifier for the conversation.
        user_id: User identifier for the conversation.
    """

    text: str
    files: List[ImageData] = []
    session_id: str = "default_session"
    user_id: str = "default_user"


class ChatResponse(BaseModel):
    """Model for a chat response.

    Attributes:
        response: The text response from the model.
        thinking_process: Optional thinking process of the model.
        attachments: List of image data to be displayed to the user.
        error: Optional error message if something went wrong.
    """

    response: str
    thinking_process: str = ""
    attachments: List[ImageData] = []
    error: Optional[str] = None


class OutputFormat(BaseModel):
    """Model for output format of the expense manager agent.

    Attributes:
        thinking_process: The thought process of the expense manager agent.
        final_response: The response to user query of the expense manager agent.
        attachment_ids: List of image hash IDs to be attached.
    """

    thinking_process: str = Field(
        description="The thought process of the expense manager agent."
    )
    final_response: str = Field(
        description="The response to user query of the expense manager agent."
    )
    attachment_ids: list[str] = Field([], description="The list of attachments IDs.")
