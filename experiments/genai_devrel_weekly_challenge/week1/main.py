"""Gradio web interface for the Gemma 2 chatbot with persistent chat history."""

from typing import Generator

import gradio as gr
from settings import get_settings
from langchain_core.messages import convert_to_openai_messages
from graph import GraphManager

settings = get_settings()
graph_manager = GraphManager()


def show_user_recent_history(
    user_message: str, thread_id: str, history: list[dict[str, str]]
) -> tuple[str, list[dict[str, str]]]:
    """Add user message to chat history.

    Args:
        user_message: The message sent by the user
        thread_id: Identifier for the chat thread
        history: Current chat history

    Returns:
        A tuple containing an empty string (to clear input) and updated history
    """
    return "", history + [{"role": "user", "content": user_message}]


def get_bot_response(
    thread_id: str, history: list[dict[str, str]]
) -> Generator[list[dict[str, str]], None, None]:
    """Generate streaming bot responses and update chat history.

    Args:
        thread_id: Identifier for the chat thread
        history: Current chat history

    Yields:
        Updated chat history with each response chunk
    """
    if thread_id == "":
        thread_id = "default"

    prev_history = history.copy()
    history.append({"role": "assistant", "content": ""})

    for chunk in graph_manager.graph.stream(
        {"messages": prev_history},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="custom",
    ):
        history[-1]["content"] += chunk
        yield history


def fetch_history(thread_id: str) -> list[dict[str, str]]:
    """Fetch chat history for a given thread from the database.

    Args:
        thread_id: Identifier for the chat thread

    Returns:
        List of chat messages in {"role": "user|assistant", "content": str} format
    """
    if thread_id == "":
        thread_id = "default"

    graph_state = graph_manager.graph.get_state(
        {"configurable": {"thread_id": thread_id}}
    )
    if "messages" not in graph_state[0]:
        return []

    return convert_to_openai_messages(graph_state[0]["messages"])


# Initialize Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# Your Chatbot")

    with gr.Row():
        thread_id = gr.Textbox(label="Thread ID", placeholder="Enter thread ID")
        refresh = gr.Button("🔄 Refresh Thread History")

    chatbot = gr.Chatbot(type="messages")
    msg = gr.Textbox(label="Input Message", placeholder="Enter message", scale=1)

    msg.submit(
        show_user_recent_history, [msg, thread_id, chatbot], [msg, chatbot], queue=False
    ).then(get_bot_response, [thread_id, chatbot], chatbot)
    refresh.click(fetch_history, [thread_id], chatbot, queue=False)

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
)
