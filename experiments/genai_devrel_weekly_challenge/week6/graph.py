"""
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from typing import Annotated, Any

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph.message import add_messages
from langgraph.types import StreamWriter
from settings import get_settings
from langchain_core.messages import AIMessage, BaseMessage
from psycopg import Connection
from langgraph.checkpoint.postgres import PostgresSaver
from google import genai
from google.genai.types import Part, Content, GenerateContentConfig
from logger import logger
from index import initialize_firebase
from settings import IMAGE_EMBEDDING_DIMENSION, EMBEDDING_FIELD_NAME
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
import os
import tempfile
import hashlib
from google.cloud import storage
import PIL.Image

settings = get_settings()
MODEL = "gemini-2.0-flash-001"
SYSTEM_PROMPT = """
You are a helpful travel agent assistant.
You can help users to answer questions about travel, 
book travel, and learn about places they are going to go.
Provides users ways to get help about their specific travel plans.
"""
DOCS_VECTOR_STORE, IMAGE_COLLECTION, MULTIMODAL_EMBEDDINGS = initialize_firebase()

# Create a temporary directory for cached files
TEMP_DIR = tempfile.mkdtemp(prefix="gcs_cache_")
# Dictionary to cache file paths
FILE_CACHE = {}


def download_gcs_file(gcs_uri: str) -> str:
    """Download a file from GCS and cache it locally.

    Args:
        gcs_uri: GCS URI in the format gs://bucket-name/path/to/file

    Returns:
        str: Path to the local file
    """
    # Check if file is already in cache
    if gcs_uri in FILE_CACHE and os.path.exists(FILE_CACHE[gcs_uri]):
        logger.info(f"Using cached file for {gcs_uri}")
        return FILE_CACHE[gcs_uri]

    # Parse GCS URI
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")

    # Remove 'gs://' prefix and split into bucket and blob path
    uri_parts = gcs_uri[5:].split("/", 1)
    if len(uri_parts) != 2:
        raise ValueError(f"Invalid GCS URI format: {gcs_uri}")

    bucket_name, blob_path = uri_parts

    # Create a hash of the URI to use as filename
    file_hash = hashlib.md5(gcs_uri.encode()).hexdigest()
    file_ext = os.path.splitext(blob_path)[1]
    local_path = os.path.join(TEMP_DIR, f"{file_hash}{file_ext}")

    # Download file if it doesn't exist
    if not os.path.exists(local_path):
        logger.info(f"Downloading {gcs_uri} to {local_path}")
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.download_to_filename(local_path)

    # Cache the file path
    FILE_CACHE[gcs_uri] = local_path
    return local_path


class State(TypedDict):
    """Type definition for the chat state.

    Attributes:
        messages: A list of chat messages that gets updated using the add_messages function.
                  The `add_messages` function in the annotation defines how this state key should be updated
                  (in this case, it appends messages to the list, rather than overwriting them)
    """

    messages: Annotated[list[BaseMessage], add_messages]


def format_chat_to_gemini_standard(messages: list) -> list[Content]:
    converted_messages = []
    for message in messages:
        if isinstance(message, AIMessage):
            converted_messages.append(
                Content(role="model", parts=[Part.from_text(text=message.content)])
            )
        else:
            converted_messages.append(
                Content(role="user", parts=[Part.from_text(text=message.content)])
            )

    return converted_messages


def get_model_response(
    state: State, config: RunnableConfig, writer: StreamWriter
) -> dict[str, list[AIMessage]]:
    """Generate a streaming response from Gemini

    Args:
        state: The current state containing chat message history
        writer: A StreamWriter object to handle streaming responses
        config: The configuration for the runnable

    Returns:
        dict containing the new AI message to be added to the chat history

    Example:
        {
            "messages": [AIMessage(content="Complete response from Gemini")]
        }
    """
    global SYSTEM_PROMPT

    # TODO: refactor to tool node
    relevant_contexts = get_relevant_contexts(state["messages"][-1].content)
    relevant_photos = get_relevant_photos(state["messages"][-1].content)

    SYSTEM_PROMPT_TEXT = (
        SYSTEM_PROMPT
        + f"""
Utilize the following context to generate a response if they're relevant:

## Text Contexts
{relevant_contexts}

## Photo Contexts
"""
    )

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Convert messages to the format expected by the Gemini API
    converted_messages = format_chat_to_gemini_standard(state["messages"][:-1])

    # Create system instruction with text prompt
    user_added_photo_context = [
        """
## Additional Insights

This is photos of activities that the user might be interested in,
DO NOT mention references to these photos in your response.

"""
    ]

    for photo in relevant_photos:
        try:
            # Download the file if needed and get local path
            local_file_path = download_gcs_file(photo)

            pil_image = PIL.Image.open(local_file_path)

            # Add the image to the context using local file
            user_added_photo_context.append(pil_image)

        except Exception as e:
            logger.error(f"Error processing photo {photo}: {str(e)}")

    chat_model = client.chats.create(
        model=MODEL,
        history=converted_messages,
        config=GenerateContentConfig(system_instruction=SYSTEM_PROMPT_TEXT),
    )

    try:
        response = chat_model.send_message_stream(
            [
                Part.from_text(text=state["messages"][-1].content),
                *user_added_photo_context,
            ]
        )

        full_response: list[str] = []
        for chunk in response:
            json_fields = {
                "response": chunk.dict(),
            }
            logger.debug(
                "gemini response is generated", extra={"json_fields": json_fields}
            )

            writer(chunk.text)
            full_response.append(chunk.text)
    except Exception as e:
        writer(f"failed to generate response: {e}")
        logger.error(f"failed to genereate gemini response: {e}")
        return {"messages": []}

    return {"messages": [AIMessage(content="".join(full_response))]}


def get_relevant_contexts(text: str) -> list[str]:
    results = DOCS_VECTOR_STORE.similarity_search(text, k=10)
    contexts = [result.page_content for result in results]
    return contexts


def get_relevant_photos(text: str) -> list[str]:
    embeddings = MULTIMODAL_EMBEDDINGS.get_embeddings(
        contextual_text=text,
        dimension=IMAGE_EMBEDDING_DIMENSION,
    )
    # Requires a single-field vector index
    query_result = IMAGE_COLLECTION.find_nearest(
        vector_field=EMBEDDING_FIELD_NAME,
        query_vector=Vector(embeddings.text_embedding),
        distance_measure=DistanceMeasure.COSINE,
        limit=5,
    )

    return [doc.to_dict()["image_path"] for doc in query_result.stream()]


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
