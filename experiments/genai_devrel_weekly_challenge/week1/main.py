from turtle import title
import gradio as gr
import random
import time

def user(user_message, thread_id, history):
    print(thread_id)
    return "",history + [{"role": "user", "content": user_message}]

def get_bot_response(thread_id, history):
    print(history[-1],thread_id)
    bot_message = random.choice(["How are you?", "I love you", "I'm very hungry"])
    history.append({"role": "assistant", "content": ""})
    for character in bot_message:
        history[-1]['content'] += character
        time.sleep(0.05)
        yield history

def fetch_history(thread_id: str):
    # Simulate fetching history from a backend
    # In real implementation, you would fetch from your backend based on thread_id
    sample_history = [
        {"role": "user", "content": f"Starting chat with thread {thread_id}"},
        {"role": "assistant", "content": "Hello! How can I help you today?"},
        {"role": "user", "content": "This is a previous message"},
        {"role": "assistant", "content": "This is a previous response"}
    ]
    return sample_history

with gr.Blocks() as demo:
    gr.Markdown("# Your Chatbot")
    
    with gr.Row():
        thread_id = gr.Textbox(label="Thread ID", placeholder="Enter thread ID", scale=1)
        backend = gr.Dropdown(
            choices=["ollama-gemma", "gemini"],
            label="Backend",
            value="ollama-gemma",
            scale=1
        )
    refresh = gr.Button("🔄 Refresh Thread History")

    chatbot = gr.Chatbot(type="messages")
    msg = gr.Textbox(label="Input Message", placeholder="Enter message", scale=1)

    msg.submit(user, [msg, thread_id, chatbot], [msg, chatbot], queue=False).then(
        get_bot_response, [thread_id, chatbot], chatbot
    )
    refresh.click(fetch_history, [thread_id], chatbot, queue=False)

demo.launch()