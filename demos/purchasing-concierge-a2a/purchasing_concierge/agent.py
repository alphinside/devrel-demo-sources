from .purchasing_agent import PurchasingAgent

root_agent = PurchasingAgent(
    remote_agent_addresses=["http://localhost:10000", "http://localhost:10001"]
).create_agent()
