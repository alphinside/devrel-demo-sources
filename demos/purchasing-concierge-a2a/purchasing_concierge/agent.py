from .purchasing_agent import PurchasingAgent

root_agent = PurchasingAgent(
    remote_agent_addresses=["http://localhost:10000"]
).create_agent()
