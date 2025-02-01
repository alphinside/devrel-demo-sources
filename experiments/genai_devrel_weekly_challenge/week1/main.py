"""Gradio web interface for the Gemma 2 chatbot with persistent chat history."""

from typing import Any, Generator, Optional

import gradio as gr
from settings import get_settings
from graph import get_gemma2_graph
from psycopg import Connection
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import convert_to_openai_messages

settings = get_settings()


class ChatbotManager:
    """Manages the chatbot's connection to PostgreSQL and graph compilation.

    This class handles the database connection setup and cleanup, as well as
    maintaining the compiled graph instance for the chatbot.

    Attributes:
        conn: PostgreSQL database connection
        checkpointer: PostgreSQL saver for persisting chat history
        compiled_graph: Compiled instance of the chatbot graph
    """

    def __init__(self) -> None:
        """Initialize the ChatbotManager with empty connection and graph."""
        self.conn: Optional[Connection] = None
        self.checkpointer: Optional[PostgresSaver] = None
        self.compiled_graph: Any = None  # Type Any due to langgraph's dynamic typing
        self.setup_connection()

    def setup_connection(self) -> None:
        """Set up the PostgreSQL connection and initialize the graph.

        Establishes a connection to PostgreSQL using settings from the configuration,
        initializes the checkpointer, and compiles the chatbot graph.
        """
        connection_kwargs: dict[str, Any] = {
            "autocommit": True,
            "prepare_threshold": 0,
        }
        if self.conn is None:
            self.conn = Connection.connect(
                settings.chat_history_db_uri, **connection_kwargs
            )
            self.checkpointer = PostgresSaver(self.conn)
            self.checkpointer.setup()
            self.compiled_graph = get_gemma2_graph().compile(
                checkpointer=self.checkpointer
            )

    def __del__(self) -> None:
        """Clean up database connection on object destruction."""
        if self.conn:
            self.conn.close()


# Initialize the chatbot manager as a global instance
chatbot_manager = ChatbotManager()


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

    for chunk in chatbot_manager.compiled_graph.stream(
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

    graph_state = chatbot_manager.compiled_graph.get_state(
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

demo.launch()
