from expense_manager_agent.agent import root_agent as expense_manager_agent
from structure_formatting_agent.agent import root_agent as structure_formatting_agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.events import Event
from fastapi import FastAPI, Body, Depends
from typing import AsyncIterator
from types import SimpleNamespace
from google.genai import types
import uvicorn
from contextlib import asynccontextmanager
import asyncio
from utils import (
    download_image_from_gcs,
    format_user_request_to_adk_content_and_store_artifacts,
)
from schema import ImageData, ChatRequest, ChatResponse, OutputFormat
import logger
from google.adk.artifacts import GcsArtifactService
from settings import get_settings
import json

SETTINGS = get_settings()
APP_NAME = "expense_manager_app"


# Application state to hold service contexts
class AppContexts(SimpleNamespace):
    """A class to hold application contexts with attribute access"""

    session_service: InMemorySessionService = None
    artifact_service: GcsArtifactService = None
    expense_manager_agent_runner: Runner = None
    structure_formatting_agent_runner: Runner = None


# Initialize application state
app_contexts = AppContexts()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize service contexts during application startup
    app_contexts.session_service = InMemorySessionService()
    app_contexts.artifact_service = GcsArtifactService(
        bucket_name=SETTINGS.STORAGE_BUCKET_NAME
    )
    app_contexts.expense_manager_agent_runner = Runner(
        agent=expense_manager_agent,
        app_name=APP_NAME,
        session_service=app_contexts.session_service,
        artifact_service=app_contexts.artifact_service,
    )
    app_contexts.structure_formatting_agent_runner = Runner(
        agent=structure_formatting_agent,
        app_name=APP_NAME,
        session_service=app_contexts.session_service,
    )

    logger.info("Application started successfully")
    yield
    logger.info("Application shutting down")
    # Perform cleanup during application shutdown if necessary


# Helper function to get application state as a dependency
async def get_app_contexts() -> AppContexts:
    return app_contexts


# Create FastAPI app
app = FastAPI(title="Personal Expense Assistant API", lifespan=lifespan)


async def process_agent_response(
    session_service: InMemorySessionService,
    runner: Runner,
    user_id: str,
    session_id: str,
    content: types.Content,
) -> str:
    """
    Process the message with the agent and extract the final response.

    Args:
        app_context: The application context containing agent runners
        user_id: The user ID for the session
        session_id: The session ID for the conversation
        content: The message content to process

    Returns:
        The final response text from the agent
    """
    # Type annotation: runner.run_async returns an AsyncIterator[Event]
    # Create session if it doesn't exist
    if not session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=f"{session_id}_{runner.agent.name}",
    ):
        session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=f"{session_id}_{runner.agent.name}",
        )

    events_iterator: AsyncIterator[Event] = runner.run_async(
        user_id=user_id,
        session_id=f"{session_id}_{runner.agent.name}",
        new_message=content,
    )
    final_response_text = ""
    async for event in events_iterator:  # event has type Event
        # Key Concept: is_final_response() marks the concluding message for the turn
        if event.is_final_response():
            if event.content and event.content.parts:
                # Extract text from the first part
                final_response_text = event.content.parts[0].text
            break  # Stop processing events once the final response is found

    logger.info(
        f"Received final response from agent {runner.agent.name}",
        raw_final_response=final_response_text,
    )
    return final_response_text


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest = Body(...),
    app_context: AppContexts = Depends(get_app_contexts),
) -> ChatResponse:
    """Process chat request and get response from the agent"""

    # Prepare the user's message in ADK format and store image artifacts
    content: types.Content = await asyncio.to_thread(
        format_user_request_to_adk_content_and_store_artifacts,
        request=request,
        app_name=APP_NAME,
        artifact_service=app_context.artifact_service,
    )

    final_response_text = "Agent did not produce a final response."  # Default

    # Use the session ID from the request or default if not provided
    session_id = request.session_id
    user_id = request.user_id

    try:
        # Process the message with the agent and get the final response
        final_response_text = await process_agent_response(
            session_service=app_context.session_service,
            runner=app_context.expense_manager_agent_runner,
            user_id=user_id,
            session_id=session_id,
            content=content,
        )

        structured_response = await process_agent_response(
            session_service=app_context.session_service,
            runner=app_context.structure_formatting_agent_runner,
            user_id=user_id,
            session_id=session_id,
            content=types.Content(
                parts=[
                    types.Part(
                        text=f"Format the following response into JSON:\n\n{final_response_text}"
                    )
                ]
            ),
        )

        output_format = OutputFormat(**json.loads(structured_response))

        # Extract and process any attachments and thinking process in the response
        base64_attachments = []
        # Download images from GCS and replace hash IDs with base64 data
        for image_hash_id in output_format.attachment_ids:
            # Download image data and get MIME type
            result = await asyncio.to_thread(
                download_image_from_gcs,
                artifact_service=app_context.artifact_service,
                image_hash=image_hash_id,
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )
            if result:
                base64_data, mime_type = result
                base64_attachments.append(
                    ImageData(serialized_image=base64_data, mime_type=mime_type)
                )

        logger.info(
            "Processed response with attachments",
            sanitized_response=output_format.final_response,
            thinking_process=output_format.thinking_process,
            attachment_ids=output_format.attachment_ids,
        )

        return ChatResponse(
            response=output_format.final_response,
            thinking_process=output_format.thinking_process,
            attachments=base64_attachments,
        )

    except Exception as e:
        logger.error("Error processing chat request", error_message=str(e))
        return ChatResponse(
            response="", error=f"Error in generating response: {str(e)}"
        )


# Only run the server if this file is executed directly
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
