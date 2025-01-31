import gradio as gr
from settings import get_settings
from graph import get_chatbot_graph
from psycopg import Connection
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import convert_to_openai_messages

settings = get_settings()


class ChatbotManager:
    def __init__(self):
        self.conn = None
        self.checkpointer = None
        self.compiled_graph = None
        self.setup_connection()

    def setup_connection(self):
        connection_kwargs = {
            "autocommit": True,
            "prepare_threshold": 0,
        }
        if self.conn is None:
            self.conn = Connection.connect(
                settings.chat_history_db_uri, **connection_kwargs
            )
            self.checkpointer = PostgresSaver(self.conn)
            self.checkpointer.setup()
            self.compiled_graph = get_chatbot_graph().compile(
                checkpointer=self.checkpointer
            )

    def __del__(self):
        if self.conn:
            self.conn.close()


# Initialize the chatbot manager as a global instance
chatbot_manager = ChatbotManager()


def show_user_recent_history(user_message, thread_id, history):
    return "", history + [{"role": "user", "content": user_message}]


def get_bot_response(thread_id, history):
    if thread_id == "":
        thread_id = "default"

    prev_history = history.copy()
    history.append({"role": "assistant", "content": ""})

    for chunk in chatbot_manager.compiled_graph.stream(
        {"messages": prev_history},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="custom",
    ):
        history[-1]["content"] += chunk
        yield history


def fetch_history(thread_id: str):
    if thread_id == "":
        thread_id = "default"

    graph_state = chatbot_manager.compiled_graph.get_state(
        {"configurable": {"thread_id": thread_id}}
    )
    if "messages" not in graph_state[0]:
        return []

    return convert_to_openai_messages(graph_state[0]["messages"])


with gr.Blocks() as demo:
    gr.Markdown("# Your Chatbot")

    with gr.Row():
        thread_id = gr.Textbox(label="Thread ID", placeholder="Enter thread ID")

        refresh = gr.Button("🔄 Refresh Thread History")

    chatbot = gr.Chatbot(type="messages")
    msg = gr.Textbox(label="Input Message", placeholder="Enter message", scale=1)

    msg.submit(
        show_user_recent_history, [msg, thread_id, chatbot], [msg, chatbot], queue=False
    ).then(get_bot_response, [thread_id, chatbot], chatbot)
    refresh.click(fetch_history, [thread_id], chatbot, queue=False)

demo.launch()
