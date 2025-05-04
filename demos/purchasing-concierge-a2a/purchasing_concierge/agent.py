from .purchasing_agent import PurchasingAgent

root_agent = PurchasingAgent(
    remote_agent_addresses=[
        "https://pizza-agent-1017509349710.us-central1.run.app",
        "https://burger-agent-1017509349710.us-central1.run.app",
    ]
).create_agent()
