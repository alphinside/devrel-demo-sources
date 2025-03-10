import gradio as gr
from google.genai.types import Content, Part
from google.genai import Client
from settings import get_settings

settings = get_settings()
GENAI_CLIENT = Client(api_key=settings.GEMINI_API_KEY)
GEMINI_MODEL_NAME = "gemini-2.0-flash-001"
SYSTEM_PROMPT = """
You are a helpful assistant. You are expert at analyzing given documents or images.
"""


def format_chat_to_gemini_standard(messages: list) -> list[Content]:
    converted_messages = []
    for message in messages:
        breakpoint()
        # if isinstance(message, AIMessage):
        #     converted_messages.append(
        #         Content(role="model", parts=[Part.from_text(text=message.content)])
        #     )
        # else:
        #     converted_messages.append(
        #         Content(role="user", parts=[Part.from_text(text=message.content)])
        #     )

    return converted_messages


def get_gemini_multimodal_response(message: dict, history: list[dict]):
    _ = format_chat_to_gemini_standard(history)
    chat_model = GENAI_CLIENT.chats.create(
        model=GEMINI_MODEL_NAME,
        # history=converted_messages,
        config={"system_instruction": SYSTEM_PROMPT},
    )

    # Prepare multimodal message in "files"
    content_parts = []
    if message.get("files", []):
        # TODO handle files input
        pass

    content_parts.append(Part.from_text(text=message["text"]))

    content = Content(role="user", parts=content_parts)

    response = chat_model.send_message(content)

    return response.text


demo = gr.ChatInterface(
    get_gemini_multimodal_response,
    type="messages",
    multimodal=True,
    textbox=gr.MultimodalTextbox(file_count="multiple"),
)

demo.launch()
