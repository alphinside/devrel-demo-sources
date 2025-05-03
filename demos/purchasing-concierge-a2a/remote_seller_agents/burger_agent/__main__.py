from common.server import A2AServer
from common.types import AgentCard, AgentCapabilities, AgentSkill, AgentAuthentication
from common.utils.push_notification_auth import PushNotificationSenderAuth
from remote_seller_agents.burger_agent.task_manager import AgentTaskManager
from remote_seller_agents.burger_agent.agent import BurgerSellerAgent
import click
import logging
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--host", "host", default="0.0.0.0")
@click.option("--port", "port", default=10001)
def main(host, port):
    """Starts the Burger Seller Agent server."""
    try:
        capabilities = AgentCapabilities(pushNotifications=True)
        skill = AgentSkill(
            id="create_burger_order",
            name="Burger Order Creation Tool",
            description="Helps with creating burger orders",
            tags=["burger order creation"],
            examples=["I want to order 2 classic cheeseburgers"],
        )
        agent_card = AgentCard(
            name="burger_seller_agent",
            description="Helps with creating burger orders",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            authentication=AgentAuthentication(schemes=["Basic"]),
            defaultInputModes=BurgerSellerAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=BurgerSellerAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        notification_sender_auth = PushNotificationSenderAuth()
        notification_sender_auth.generate_jwk()
        server = A2AServer(
            agent_card=agent_card,
            task_manager=AgentTaskManager(
                agent=BurgerSellerAgent(),
                notification_sender_auth=notification_sender_auth,
            ),
            host=host,
            port=port,
            auth_username=os.environ.get("AUTH_USERNAME"),
            auth_password=os.environ.get("AUTH_PASSWORD"),
        )

        server.app.add_route(
            "/.well-known/jwks.json",
            notification_sender_auth.handle_jwks_endpoint,
            methods=["GET"],
        )

        logger.info(f"Starting server on {host}:{port}")
        server.start()
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()
