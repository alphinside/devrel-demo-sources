from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import StreamWriter
from settings import get_settings
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from langchain_core.messages import AIMessage, BaseMessage, convert_to_openai_messages
import json


settings = get_settings()


class State(TypedDict):
    """Type definition for the chat state.

    Attributes:
        messages: A list of chat messages that gets updated using the add_messages function.
                  The `add_messages` function in the annotation defines how this state key should be updated
                  (in this case, it appends messages to the list, rather than overwriting them)
    """

    messages: Annotated[list[BaseMessage], add_messages]


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
    url = f"{settings.ollama_service_url}/api/chat"
    creds = service_account.IDTokenCredentials.from_service_account_file(
        settings.cloudrun_service_account_key, target_audience=url
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


# Initialize the chat graph
gemma2_graph = StateGraph(State)
gemma2_graph.add_node("gemma2", get_gemma2_response)
gemma2_graph.add_edge(START, "gemma2")
gemma2_graph.add_edge("gemma2", END)


def get_gemma2_graph() -> StateGraph:
    """Return the initialized chatbot graph.

    Returns:
        A configured StateGraph instance that handles the chat flow using Gemma 2.
    """
    return gemma2_graph
