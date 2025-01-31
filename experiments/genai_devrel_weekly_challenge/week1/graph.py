from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import StreamWriter
from settings import get_settings
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from langchain_core.messages import AIMessage, convert_to_openai_messages
import json


settings = get_settings()


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


def get_gemma2_response(state: State, writer: StreamWriter):
    url = f"{settings.ollama_service_url}/api/chat"
    creds = service_account.IDTokenCredentials.from_service_account_file(
        settings.cloudrun_service_account_key, target_audience=url
    )
    authed_session = AuthorizedSession(creds)

    converted_messages = convert_to_openai_messages(state["messages"])
    data = {"model": "gemma2:9b", "messages": converted_messages}
    full_response = []
    with authed_session.post(url, json=data, stream=True) as response:
        for line in response.iter_lines():
            response = json.loads(line.decode("utf-8"))

            writer(response["message"]["content"])
            full_response.append(response["message"]["content"])

    return {"messages": [AIMessage(content="".join(full_response))]}


chatbot_graph = StateGraph(State)
chatbot_graph.add_node("chatbot", get_gemma2_response)
chatbot_graph.add_edge(START, "chatbot")
chatbot_graph.add_edge("chatbot", END)


def get_chatbot_graph():
    return chatbot_graph
