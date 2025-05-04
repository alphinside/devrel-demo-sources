# Purchasing Concierge A2A Demo

This demo shows how to enable A2A (Agent to Agent) protocol communication between purchasing concierge agent with the remote pizza and burger seller agents. Burger and Pizza seller agents is a independent agent that can be run on different server with different frameworks, in this demo example we, burger agent is built on top of Crew AI and pizza agent is built on top of LangGraph.

# How to Run

First, we need to run the remote seller agents. We have two remote seller agents, one is burger agent and the other is pizza agent. We need to run them separately. These agents will serve the A2A Server

## Run the Burger Agent

1. Copy the `remote_seller_agents/burger_agent/.env.example` to `remote_seller_agents/burger_agent/.env`.
2. Fill in the required environment variables in the `.env` file. Substitute `GCLOUD_PROJECT_ID` with your Google Cloud Project ID.

    ```
    AUTH_USERNAME=burgeruser123
    AUTH_PASSWORD=burgerpass123
    GCLOUD_LOCATION=us-central1
    GCLOUD_PROJECT_ID={your-project-id}
    ```
3. Run the burger agent.

    ```bash
    cd remote_seller_agents/burger_agent
    uv run .
    ```

## Run the Pizza Agent

1. Copy the `remote_seller_agents/pizza_agent/.env.example` to `remote_seller_agents/pizza_agent/.env`.
2. Fill in the required environment variables in the `.env` file. Substitute `GCLOUD_PROJECT_ID` with your Google Cloud Project ID.

    ```
    API_KEY=pizza123
    GCLOUD_LOCATION=us-central1
    GCLOUD_PROJECT_ID={your-project-id}
    ```
3. Run the pizza agent.

    ```bash
    cd remote_seller_agents/pizza_agent
    uv run .
    ```

## Run the Purchasing Concierge Agent

Finally, we can run our A2A client capabilities owned by purchasing concierge agent.

1. Copy the `purchasing_concierge/.env.example` to `purchasing_concierge/.env`.
2. Fill in the required environment variables in the `.env` file. Substitute `GCLOUD_PROJECT_ID` with your Google Cloud Project ID.

    ```
    PIZZA_SELLER_AGENT_AUTH=pizza123
    PIZZA_SELLER_AGENT_URL=http://localhost:10000
    BURGER_SELLER_AGENT_AUTH=burgeruser123:burgerpass123
    BURGER_SELLER_AGENT_URL=http://localhost:10001
    GOOGLE_GENAI_USE_VERTEXAI=TRUE
    GOOGLE_CLOUD_PROJECT={your-project-id}
    GOOGLE_CLOUD_LOCATION=us-central1
    ```

3. Run the purchasing concierge agent with the UI

    ```bash
    uv run purchasing_concierge_demo.py
    ```

4. You should be able to access the UI at `http://localhost:8000`
    
    


