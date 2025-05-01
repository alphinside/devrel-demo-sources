from typing import Literal
from pydantic import BaseModel
import uuid
from crewai import Agent, Crew, LLM, Task, Process
from crewai.tools import tool
from dotenv import load_dotenv
import os

load_dotenv()


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str


class OrderItem(BaseModel):
    name: str
    quantity: int
    price: int


class Order(BaseModel):
    order_id: str
    status: str
    order_items: list[OrderItem]


@tool("create_order")
def create_order(order_items: list[OrderItem]) -> str:
    """
    Creates a new order with the given order items.

    Args:
        order_items: List of order items to be added to the order.

    Returns:
        str: A message indicating that the order has been created.
    """
    try:
        order_id = str(uuid.uuid4())
        order = Order(order_id=order_id, status="created", order_items=order_items)
        print("===")
        print(f"order created: {order}")
        print("===")
    except Exception as e:
        print(f"Error creating order: {e}")
        return f"Error creating order: {e}"
    return f"Order {order.model_dump()} has been created"


class BurgerSellerAgent:
    TaskInstruction = """
# INSTRUCTIONS

You are a specialized assistant for a burger store.
Your sole purpose is to answer questions about what is available on burger menu and price also handle order creation.
If the user asks about anything other than burger menu or order creation, politely state that you cannot help with that topic and can only assist with burger menu and order creation.
Do not attempt to answer unrelated questions or use tools for other purposes.

# CONTEXT

Received user prompt: {user_prompt}
Session ID: {session_id}

Provided below is the available burger menu and it's related price:
- Classic Cheeseburger: IDR 85K
- Double Cheeseburger: IDR 110K
- Spicy Chicken Burger: IDR 80K
- Spicy Cajun Burger: IDR 85K

# RULES

- If user want to order something, strictly follow the following steps:
    1. User want to order something
    2. Always ask for final order confirmation by specifying all the ordered items and total price 
    3. Use `create_order` tool to create the order

- ALWAYS Provide the detailed ordered items, price breakdown and total, and order ID to the user after executing `create_order` tool.
- Set response status to input_required if asking for user order confirmation.
- Set response status to error if there is an error while processing the request.
- Set response status to completed if the request is complete.
- DO NOT make up menu or price, Always rely on the provided menu given to you as context.
"""
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        # Use environment variables for configuration
        self.model = LLM(
            model="gemini-2.0-flash",  # Use base model name without provider prefix
            api_type="vertex_ai",  # Tell CrewAI to use Vertex AI
            project=os.getenv("GCLOUD_PROJECT_ID"),  # Project from env or default
            location=os.getenv(
                "GCLOUD_LOCATION"
            ),  # Region from env or default to us-central1
        )
        self.burger_agent = Agent(
            role="Burger Seller Agent",
            goal=(
                "Help user to understand what is available on burger menu and price also handle order creation."
            ),
            backstory=("You are an expert and helpful burger seller agent."),
            verbose=False,
            allow_delegation=False,
            tools=[create_order],
            llm=self.model,
        )

        self.agent_task = Task(
            description=self.TaskInstruction,
            output_pydantic=ResponseFormat,
            agent=self.burger_agent,
            expected_output=(
                "A JSON object with 'status' and 'message' fields."
                "Set response status to input_required if asking for user order confirmation."
                "Set response status to error if there is an error while processing the request."
                "Set response status to completed if the request is complete."
            ),
        )

        self.crew = Crew(
            tasks=[self.agent_task],
            agents=[self.burger_agent],
            verbose=False,
            process=Process.sequential,
            memory=True,
            embedder={
                "provider": "vertexai",
                "config": {
                    "project_id": os.getenv("GCLOUD_PROJECT_ID"),
                    "region": os.getenv("GCLOUD_LOCATION"),
                    "model_name": "text-embedding-005",
                },
            },
        )

    def invoke(self, query, sessionId) -> str:
        inputs = {"user_prompt": query, "session_id": sessionId}
        response = self.crew.kickoff(inputs)
        return response

    def get_agent_response(self, response):
        breakpoint()
        current_state = self.graph.get_state(response)
        structured_response = current_state.values.get("structured_response")
        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == "input_required":
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message,
                }
            elif structured_response.status == "error":
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message,
                }
            elif structured_response.status == "completed":
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": structured_response.message,
                }

        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": "We are unable to process your request at the moment. Please try again.",
        }


if __name__ == "__main__":
    agent = BurgerSellerAgent()
    result = agent.invoke("show me the burger menu", "default_session")
    print(result)
    result = agent.invoke("1 classic cheeseburger pls", "default_session")
    print(result)
    result = agent.invoke("okey", "default_session")
    print(result)
