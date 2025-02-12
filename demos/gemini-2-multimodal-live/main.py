import gradio as gr
from google import genai
import asyncio
import traceback
import pyaudio

MODEL = "models/gemini-2.0-flash-exp"
client = genai.Client(http_options={"api_version": "v1alpha"})
CONFIG = {
    "generation_config": {"response_modalities": ["AUDIO"]},
    "systemInstruction": "always respond in English",
}
AUDIO_FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
pya = pyaudio.PyAudio()
OPEN_MIC = True


class AudioLoop:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None

        self.session = None

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(
                input,
                "message > ",
            )
            if text.lower() == "q":
                break
            await self.session.send(input=text or ".", end_of_turn=True)

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg)

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=AUDIO_FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        while True:
            if OPEN_MIC:
                data = await asyncio.to_thread(
                    self.audio_stream.read, CHUNK_SIZE, **kwargs
                )

                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
            else:
                await asyncio.sleep(0.01)

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        while True:
            turn = self.session.receive()
            async for response in turn:
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                    continue
                if text := response.text:
                    print(text, end="")

            # If you interrupt the model, it sends a turn_complete.
            # For interruptions to work, we need to stop playback.
            # So empty out the audio queue because it may have loaded
            # much more audio than has played yet.
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=AUDIO_FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            frames_per_buffer=CHUNK_SIZE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session

                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)

                # send_text_task = tg.create_task(self.send_text())
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())

                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                while True:
                    await asyncio.sleep(0.01)

        except ExceptionGroup as EG:
            self.audio_stream.close()
            traceback.print_exception(EG)


with gr.Blocks() as demo:
    audio_loop = AudioLoop()

    with gr.Row():
        interrupt_mic = gr.Button("Stop Mic")
        session_button = gr.Button("Start Session")

    async def start_session(audio_loop=audio_loop):
        if audio_loop.session is None:
            audio_loop._task = asyncio.create_task(audio_loop.run())
            return "Stop Session"
        else:
            if audio_loop._task:
                audio_loop._task.cancel()
            audio_loop.session = None
            return "Start Session"

    session_button.click(
        start_session,
        outputs=session_button,
    )

    async def toggle_mic_input():
        global OPEN_MIC

        OPEN_MIC = not OPEN_MIC

        if OPEN_MIC:
            return "Stop Mic"
        else:
            return "Start Mic"

    interrupt_mic.click(
        toggle_mic_input,
        outputs=interrupt_mic,
    )

    # async def start_mic_input(audio_loop=audio_loop):
    #     if audio_loop.audio_stream is None:
    #         audio_loop._task = asyncio.create_task(audio_loop.run_audio_input_stream())
    #         return "Stop Mic"
    #     else:
    #         if audio_loop._task:
    #             audio_loop._task.cancel()
    #         audio_loop.audio_stream = None
    #         return "Start Mic"

    # mic_button.click(
    #     start_mic_input,
    #     outputs=mic_button,
    # )

demo.launch()
