from typing import Annotated, Any

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph.message import add_messages
from langgraph.types import StreamWriter
from settings import get_settings
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from langchain_core.messages import AIMessage, BaseMessage, convert_to_openai_messages
import json
from psycopg import Connection
from langgraph.checkpoint.postgres import PostgresSaver
from google import genai
from google.genai.types import Content, Part

settings = get_settings()


class State(TypedDict):
    """Type definition for the chat state.

    Attributes:
        messages: A list of chat messages that gets updated using the add_messages function.
                  The `add_messages` function in the annotation defines how this state key should be updated
                  (in this case, it appends messages to the list, rather than overwriting them)
    """

    messages: Annotated[list[BaseMessage], add_messages]


def get_model_response(
    state: State, config: RunnableConfig, writer: StreamWriter
) -> dict[str, list[AIMessage]]:
    model_choice = config["configurable"]["model"]

    if model_choice == "gemma2":
        return get_gemma2_response(state, writer)
    elif model_choice == "gemini":
        return get_gemini_response(state, writer)
    else:
        raise ValueError(
            f"Unknown model: {model_choice}, only gemma2 and gemini are supported"
        )


def get_gemma2_response(
    state: State, writer: StreamWriter
) -> dict[str, list[AIMessage]]:
    """Generate a streaming response from Gemma 2 model via Ollama service.

    This function authenticates with Cloud Run, sends the chat history to the Ollama service,
    and streams the response back to the client.

    Args:
        state: The current state containing chat message history
        writer: A StreamWriter object to handle streaming responses

    Returns:
        dict containing the new AI message to be added to the chat history

    Example:
        {
            "messages": [AIMessage(content="Complete response from Gemma")]
        }
    """
    url = f"{settings.OLLAMA_SERVICE_URL}/api/chat"
    creds = service_account.IDTokenCredentials.from_service_account_file(
        settings.CLOUDRUN_SERVICE_ACCOUNT_KEY, target_audience=url
    )
    authed_session = AuthorizedSession(creds)

    converted_messages = convert_to_openai_messages(state["messages"])
    data = {"model": "gemma2:9b", "messages": converted_messages}
    full_response: list[str] = []

    # Because we are not using Langchain ChatModel object, we have to manually
    # stream the response from the Ollama service and using Langgraph "custom"
    # stream mode later on when invoking `graph.stream`
    with authed_session.post(url, json=data, stream=True) as response:
        for line in response.iter_lines():
            response = json.loads(line.decode("utf-8"))

            writer(response["message"]["content"])
            full_response.append(response["message"]["content"])

    return {"messages": [AIMessage(content="".join(full_response))]}


def get_gemini_response(
    state: State, writer: StreamWriter
) -> dict[str, list[AIMessage]]:
    """Generate a streaming response from Gemini 2.0 Flash

    Args:
        state: The current state containing chat message history
        writer: A StreamWriter object to handle streaming responses

    Returns:
        dict containing the new AI message to be added to the chat history

    Example:
        {
            "messages": [AIMessage(content="Complete response from Gemini")]
        }
    """
    # url = f"{settings.OLLAMA_SERVICE_URL}/api/chat"
    # creds = service_account.IDTokenCredentials.from_service_account_file(
    #     settings.CLOUDRUN_SERVICE_ACCOUNT_KEY, target_audience=url
    # )
    # authed_session = AuthorizedSession(creds)

    # converted_messages = convert_to_openai_messages(state["messages"])
    # data = {"model": "gemini-2.0-flash:9b", "messages": converted_messages}
    # full_response: list[str] = []

    # with authed_session.post(url, json=data, stream=True) as response:
    #     for line in response.iter_lines():
    #         response = json.loads(line.decode("utf-8"))

    #         writer(response["message"]["content"])
    #         full_response.append(response["message"]["content"])
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    converted_messages = []
    for message in state["messages"][:-1]:
        if isinstance(message, AIMessage):
            converted_messages.append(
                Content(role="model", parts=[Part.from_text(text=message.content)])
            )
        else:
            converted_messages.append(
                Content(role="user", parts=[Part.from_text(text=message.content)])
            )

    chat_model = client.chats.create(
        model="gemini-2.0-flash",
        history=converted_messages,
    )

    response = chat_model.send_message_stream(state["messages"][-1].content)
    full_response: list[str] = []
    for chunk in response:
        writer(chunk.text)
        full_response.append(chunk.text)

    return {"messages": [AIMessage(content="".join(full_response))]}


# Initialize the chat graph
graph = StateGraph(State)
graph.add_node("model", get_model_response)
graph.add_edge(START, "model")
graph.add_edge("model", END)


class GraphManager:
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
        self.conn: Connection | None = None
        self.checkpointer: PostgresSaver | None = None
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
                settings.CHAT_HISTORY_DB_URI, **connection_kwargs
            )
            self.checkpointer = PostgresSaver(self.conn)
            self.checkpointer.setup()
            self.graph = graph.compile(checkpointer=self.checkpointer)

    def __del__(self) -> None:
        """Clean up database connection on object destruction."""
        if self.conn:
            self.conn.close()
