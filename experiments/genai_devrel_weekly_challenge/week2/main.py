"""Gradio web interface for the Gemma 2 chatbot with persistent chat history."""

from typing import Generator
import psycopg
import gradio as gr
from settings import get_settings
from langchain_core.messages import convert_to_openai_messages, RemoveMessage
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
    thread_id: str, model: str, prompt_version: str, history: list[dict[str, str]]
) -> Generator[list[dict[str, str]], None, None]:
    """Generate streaming bot responses and update chat history.

    Args:
        thread_id: Identifier for the chat thread
        model: Model to use for generating responses
        prompt_version: Version of the prompt to use
        history: Current chat history

    Yields:
        Updated chat history with each response chunk
    """
    prev_history = history.copy()
    history.append({"role": "assistant", "content": ""})

    for chunk in graph_manager.graph.stream(
        {"messages": prev_history},
        config={
            "configurable": {
                "thread_id": thread_id,
                "model": model,
                "prompt_version": prompt_version,
            }
        },
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
    graph_state = graph_manager.graph.get_state(
        {"configurable": {"thread_id": thread_id}}
    )
    if "messages" not in graph_state[0]:
        return []

    return convert_to_openai_messages(graph_state[0]["messages"])


def clear_history(thread_id: str) -> list[dict[str, str]]:
    """Clear chat history for a given thread from the database.

    Args:
        thread_id: Identifier for the chat thread

    Returns:
        List of chat messages in {"role": "user|assistant", "content": str} format
    """
    config = {"configurable": {"thread_id": thread_id}}

    for message in graph_manager.graph.get_state(config).values["messages"]:
        graph_manager.graph.update_state(
            config, {"messages": RemoveMessage(id=message.id)}
        )

    return []


def get_prompt_versions() -> list[str]:
    """Fetch all prompt versions from the database.

    Returns:
        List of version strings ordered by version number
    """
    with psycopg.connect(settings.CHAT_HISTORY_DB_URI) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT version FROM prompt_versions ORDER BY version")
            return [row[0] for row in cursor.fetchall()]


# Initialize Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# Your Chatbot")

    with gr.Row():
        thread_id = gr.Textbox(label="Thread ID", value="default", interactive=True)

        with gr.Column():
            refresh = gr.Button("🔄 Refresh Thread History")
            clear = gr.Button("🗑️ CLEAR Thread History")

        model = gr.Dropdown(
            choices=["gemma2", "gemini-2.0-flash"],
            label="Model",
            value="gemini-2.0-flash",
            interactive=True,
        )

        prompt_version = gr.Dropdown(
            choices=get_prompt_versions(),
            label="Prompt Version",
            value=get_prompt_versions()[-1] if get_prompt_versions() else None,
            interactive=True,
        )

    chatbot = gr.Chatbot(type="messages")
    msg = gr.Textbox(label="Input Message", placeholder="Enter message", scale=1)

    msg.submit(
        show_user_recent_history, [msg, thread_id, chatbot], [msg, chatbot], queue=False
    ).then(get_bot_response, [thread_id, model, prompt_version, chatbot], chatbot)
    refresh.click(fetch_history, [thread_id], chatbot, queue=False)
    clear.click(clear_history, [thread_id], chatbot, queue=False)

    demo.load(fetch_history, [thread_id], chatbot, queue=False)

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
)
