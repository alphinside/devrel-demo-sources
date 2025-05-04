from typing import Callable
import uuid
from a2a_types import (
    AgentCard,
    Task,
    TaskSendParams,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
from a2a_client.client import A2AClient
from dotenv import load_dotenv
import os

load_dotenv()

TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg, AgentCard], Task]

KNOWN_AUTH = {
    "pizza_seller_agent": os.getenv("PIZZA_SELLER_AGENT_AUTH", "api_key"),
    "burger_seller_agent": os.getenv("BURGER_SELLER_AGENT_AUTH", "user:pass"),
}


class RemoteAgentConnections:
    """A class to hold the connections to the remote agents."""

    def __init__(self, agent_card: AgentCard):
        auth = KNOWN_AUTH.get(agent_card.name, None)
        self.agent_client = A2AClient(agent_card, auth=auth)
        self.card = agent_card

        self.conversation_name = None
        self.conversation = None
        self.pending_tasks = set()

    def get_agent(self) -> AgentCard:
        return self.card

    async def send_task(
        self,
        request: TaskSendParams,
        task_callback: TaskUpdateCallback | None,
    ) -> Task | None:
        print(f"Send Remote Agent Task Request: {request.model_dump()}")
        print("=" * 100)
        response = await self.agent_client.send_task(request.model_dump())
        print(f"Send Remote Agent Task Response: {response.model_dump()}")
        print("=" * 100)
        merge_metadata(response.result, request)
        # For task status updates, we need to propagate metadata and provide
        # a unique message id.
        if (
            hasattr(response.result, "status")
            and hasattr(response.result.status, "message")
            and response.result.status.message
        ):
            merge_metadata(response.result.status.message, request.message)
            m = response.result.status.message
            if not m.metadata:
                m.metadata = {}
            if "message_id" in m.metadata:
                m.metadata["last_message_id"] = m.metadata["message_id"]
            m.metadata["message_id"] = str(uuid.uuid4())

        if task_callback:
            task_callback(response.result, self.card)
        return response.result


def merge_metadata(target, source):
    if not hasattr(target, "metadata") or not hasattr(source, "metadata"):
        return
    if target.metadata and source.metadata:
        target.metadata.update(source.metadata)
    elif source.metadata:
        target.metadata = dict(**source.metadata)
