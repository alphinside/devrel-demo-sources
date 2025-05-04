from .purchasing_agent import PurchasingAgent

root_agent = PurchasingAgent(
    remote_agent_addresses=[
        # "https://pizza-agent-1017509349710.us-central1.run.app",
        # "https://burger-agent-1017509349710.us-central1.run.app",
        "http://localhost:10000",
        "http://localhost:10001",
    ]
).create_agent()
