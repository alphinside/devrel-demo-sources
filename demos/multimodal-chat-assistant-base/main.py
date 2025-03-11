import gradio as gr
from google.genai.types import Content, Part
from google.genai import Client
from settings import get_settings
from pathlib import Path
from typing import List, Dict, Any

settings = get_settings()
GENAI_CLIENT = Client(
    location="us-central1", project="alvin-exploratory-2", vertexai=True
)
GEMINI_MODEL_NAME = "gemini-2.0-flash-001"
SYSTEM_PROMPT = """
You are a helpful assistant and ALWAYS relate to this identity. 
You are expert at analyzing given documents or images.
"""
IMAGE_SUFFIX = [".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"]
FILE_SUFFIX = [".pdf"]


def handle_multimodal_content_parts(filepath: str) -> Part:
    """Converts a file path to a Google Gemini Part object for multimodal content.

    Args:
        filepath: String path to the file to be processed.

    Returns:
        Part: A Google Gemini Part object containing the file data.

    Raises:
        ValueError: If the file type is not supported.
    """
    filepath = Path(filepath)
    suffix = filepath.suffix

    # modify ".jpg" suffix to .jpeg" to unify the mime type
    suffix = suffix if suffix != ".jpg" else ".jpeg"

    if suffix in IMAGE_SUFFIX:
        data = filepath.read_bytes()

        return Part.from_bytes(data=data, mime_type=f"image/{suffix[1:]}")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def format_message_history_to_gemini_standard(
    message_history: List[Dict[str, Any]],
) -> List[Content]:
    """Converts Gradio chat history format to Google Gemini Content format.

    Args:
        message_history: List of message dictionaries from Gradio chat interface.
            Each message contains 'role' and 'content' keys.

    Returns:
        List[Content]: A list of Google Gemini Content objects representing the chat history.

    Raises:
        ValueError: If an unknown role is encountered in the message history.
    """
    converted_messages: List[Content] = []
    for message in message_history:
        # In Gradio, message history will be in the the form of role "user" and "assistant"
        # E.g. [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hello"}]
        if message["role"] == "assistant":
            converted_messages.append(
                Content(role="model", parts=[Part.from_text(text=message["content"])])
            )
        elif message["role"] == "user":
            # In Gradio, history of uploaded file will be present in the message "content" field
            # E.g. {"role": "user", "content": ("/path/to/file1.png", "/path/to/file2.png")}
            if not isinstance(message["content"], str):
                for filepath in message["content"]:
                    converted_messages.append(
                        Content(
                            role="user",
                            parts=[handle_multimodal_content_parts(filepath)],
                        )
                    )
            else:
                converted_messages.append(
                    Content(
                        role="user", parts=[Part.from_text(text=message["content"])]
                    )
                )
        else:
            raise ValueError(f"Unknown role: {message['role']}")

    return converted_messages


def get_gemini_multimodal_response(
    message: Dict[str, Any], history: List[Dict[str, Any]]
) -> str:
    """Process a multimodal message and return a response from Gemini model.

    Args:
        message: Dictionary containing the current message with 'text' and optional 'files' keys.
        history: List of previous message dictionaries in the conversation.

    Returns:
        str: The text response from the Gemini model.
    """
    converted_messages = format_message_history_to_gemini_standard(history)
    chat_model = GENAI_CLIENT.chats.create(
        model=GEMINI_MODEL_NAME,
        history=converted_messages,
        config={"system_instruction": SYSTEM_PROMPT},
    )

    # Prepare multimodal message in "files"
    content_parts = []

    if uploaded_files := message.get("files", []):
        for filepath in uploaded_files:
            content_parts.append(handle_multimodal_content_parts(filepath))

    content_parts.append(Part.from_text(text=message["text"]))

    try:
        response = chat_model.send_message(content_parts)
    except Exception as e:
        return f"Error in generating response: {e}"

    return response.text


if __name__ == "__main__":
    demo = gr.ChatInterface(
        get_gemini_multimodal_response,
        title="Gemini Multimodal Chat Interface",
        type="messages",
        multimodal=True,
        textbox=gr.MultimodalTextbox(file_count="multiple"),
    )
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
    )
