from expense_manager_agent.agent import root_agent as expense_manager_agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.events import Event
from google.genai import types
from fastapi import FastAPI, Body, Depends
from typing import AsyncIterator
from types import SimpleNamespace
import uvicorn
from contextlib import asynccontextmanager
from utils import extract_attachment_ids_from_response, download_image_from_gcs
from schema import ImageData, ChatRequest, ChatResponse


# Application state to hold service contexts
class AppContexts(SimpleNamespace):
    """A class to hold application contexts with attribute access"""

    session_service: InMemorySessionService = None
    expense_manager_agent_runner: Runner = None


# Initialize application state
app_contexts = AppContexts()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize service contexts during application startup
    app_contexts.session_service = InMemorySessionService()
    app_contexts.expense_manager_agent_runner = Runner(
        agent=expense_manager_agent,  # The agent we want to run
        app_name=AGENT_APP_NAME,  # Associates runs with our app
        session_service=app_contexts.session_service,  # Uses our session manager
    )

    print("Application started and services initialized")
    yield
    print("Application shutting down, cleaning up resources")
    # Perform cleanup during application shutdown


# Helper function to get application state as a dependency
async def get_app_contexts() -> AppContexts:
    return app_contexts


# Create FastAPI app
app = FastAPI(title="Personal Expense Assistant API", lifespan=lifespan)
AGENT_APP_NAME = "expense_manager_app"


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest = Body(...),
    app_context: AppContexts = Depends(get_app_contexts),
) -> ChatResponse:
    """Process chat request and get response from the agent"""
    # Prepare the user's message in ADK format
    content = types.Content(role="user", parts=[types.Part(text=request.text)])

    final_response_text = "Agent did not produce a final response."  # Default

    # Use the session ID from the request or default if not provided
    session_id = request.session_id
    user_id = request.user_id

    # Create session if it doesn't exist
    if not app_context.session_service.get_session(
        app_name=AGENT_APP_NAME, user_id=user_id, session_id=session_id
    ):
        app_context.session_service.create_session(
            app_name=AGENT_APP_NAME, user_id=user_id, session_id=session_id
        )

    try:
        # Process the message with the agent
        # Type annotation: runner.run_async returns an AsyncIterator[Event]
        events_iterator: AsyncIterator[Event] = (
            app_context.expense_manager_agent_runner.run_async(
                user_id=user_id, session_id=session_id, new_message=content
            )
        )
        async for event in events_iterator:  # event has type Event
            # Key Concept: is_final_response() marks the concluding message for the turn
            if event.is_final_response():
                if event.content and event.content.parts:
                    # Extract text from the first part
                    final_response_text = event.content.parts[0].text
                elif event.actions and event.actions.escalate:
                    # Handle potential errors/escalations
                    final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
                break  # Stop processing events once the final response is found

        # Extract and process any attachments in the response
        base64_attachments = []
        attachment_ids = extract_attachment_ids_from_response(final_response_text)

        # Download images from GCS and replace hash IDs with base64 data
        for image_hash_id in attachment_ids:
            base64_data = download_image_from_gcs(image_hash_id)
            if base64_data:
                base64_attachments.append(
                    ImageData(serialized_image=base64_data, image_hash_id=image_hash_id)
                )

        return ChatResponse(
            response=final_response_text, attachments=base64_attachments
        )

    except Exception as e:
        print(f"Error in processing: {str(e)}")
        return ChatResponse(
            response="", error=f"Error in generating response: {str(e)}"
        )


# Only run the server if this file is executed directly
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
