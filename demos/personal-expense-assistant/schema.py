from pydantic import BaseModel
from typing import List, Optional


class ImageData(BaseModel):
    """Model for image data with hash identifier.

    Attributes:
        serialized_image: Optional Base64 encoded string of the image content.
    """

    serialized_image: str


class ChatRequest(BaseModel):
    """Model for a chat request.

    Attributes:
        text: The text content of the message.
        files: List of image data objects
    """

    text: str
    files: List[ImageData] = []
    session_id: str = "default_session"
    user_id: str = "default_user"


class ChatResponse(BaseModel):
    """Model for a chat response.

    Attributes:
        response: The text response from the model.
        attachments: List of image data to be displayed to the user.
        error: Optional error message if something went wrong.
    """

    response: str
    thinking_process: str = ""
    attachments: List[ImageData] = []
    error: Optional[str] = None
