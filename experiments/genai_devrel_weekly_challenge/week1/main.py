import gradio as gr
from settings import get_settings
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
import json

settings = get_settings()


def show_user_recent_history(user_message, thread_id, history):
    return "", history + [{"role": "user", "content": user_message}]


def get_bot_response(thread_id, backend, history):
    if backend != "ollama-gemma":
        unsupported_backend_message = "Sorry, backend configuration is not supported yet, I cannot respond to your message"
        history.append({"role": "assistant", "content": unsupported_backend_message})

        yield history

    history.append({"role": "assistant", "content": ""})
    url = f"{settings.ollama_service_url}/api/chat"
    creds = service_account.IDTokenCredentials.from_service_account_file(
        settings.cloudrun_service_account_key, target_audience=url
    )
    authed_session = AuthorizedSession(creds)

    data = {"model": "gemma2:9b", "messages": history}
    with authed_session.post(url, json=data, stream=True) as response:
        for line in response.iter_lines():
            response = json.loads(line.decode("utf-8"))

            history[-1]["content"] += response["message"]["content"]
            yield history


def fetch_history(thread_id: str):
    # Simulate fetching history from a backend
    # In real implementation, you would fetch from your backend based on thread_id
    sample_history = [
        {"role": "user", "content": f"Starting chat with thread {thread_id}"},
        {"role": "assistant", "content": "Hello! How can I help you today?"},
        {"role": "user", "content": "This is a previous message"},
        {"role": "assistant", "content": "This is a previous response"},
    ]
    return sample_history


with gr.Blocks() as demo:
    gr.Markdown("# Your Chatbot")

    with gr.Row():
        thread_id = gr.Textbox(
            label="Thread ID", placeholder="Enter thread ID", scale=1
        )
        backend = gr.Dropdown(
            choices=["ollama-gemma", "gemini"],
            label="Backend",
            value="ollama-gemma",
            scale=1,
        )
    refresh = gr.Button("🔄 Refresh Thread History")

    chatbot = gr.Chatbot(type="messages")
    msg = gr.Textbox(label="Input Message", placeholder="Enter message", scale=1)

    msg.submit(
        show_user_recent_history, [msg, thread_id, chatbot], [msg, chatbot], queue=False
    ).then(get_bot_response, [thread_id, backend, chatbot], chatbot)
    refresh.click(fetch_history, [thread_id], chatbot, queue=False)

demo.launch()
