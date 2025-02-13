import gradio as gr
from google import genai
import asyncio
import traceback
import numpy as np
from scipy import signal
import pyaudio


MODEL = "models/gemini-2.0-flash-exp"
client = genai.Client(http_options={"api_version": "v1alpha"})
CONFIG = {
    "generation_config": {"response_modalities": ["AUDIO"]},
    "system_instruction": (
        "Your name is Erik, always introduce yourself first before the conversation begins."
        "You are an expert in product management and can suggest best practices "
        "how to design and launch a successful product. Always explain your answer in a "
        "little bit more comprehensive so that the conversation becomes more natural."
    ),
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
        self._task = None

    def resample_audio(self, audio_data, from_rate, to_rate):
        """Resample audio data from one rate to another"""
        if from_rate == to_rate:
            return audio_data

        # Calculate resampling ratio
        ratio = to_rate / from_rate

        # Calculate new length
        new_length = int(len(audio_data) * ratio)

        # Resample using scipy.signal.resample
        resampled = signal.resample(audio_data, new_length)
        return resampled.astype(np.int16)

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
            try:
                msg = self.out_queue.get_nowait()
                await self.session.send(input=msg)
            except Exception:
                await asyncio.sleep(0.01)

    async def process_mic_input(self, audio_data):
        """Process microphone input from Gradio"""
        print(OPEN_MIC)
        if OPEN_MIC and audio_data is not None and self.out_queue is not None:
            # Gradio returns a tuple of (sample_rate, audio_data)
            sample_rate, audio_array = audio_data

            # Ensure audio is mono
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)

            # Resample from input rate to 16kHz
            resampled_data = self.resample_audio(
                audio_array, sample_rate, SEND_SAMPLE_RATE
            )

            # Process audio in chunks
            num_samples = len(resampled_data)
            for i in range(0, num_samples, CHUNK_SIZE):
                chunk = resampled_data[i : i + CHUNK_SIZE]

                # If the last chunk is smaller than CHUNK_SIZE, pad with zeros
                if len(chunk) < CHUNK_SIZE:
                    chunk = np.pad(chunk, (0, CHUNK_SIZE - len(chunk)), "constant")

                # Convert chunk to bytes
                chunk_bytes = chunk.tobytes()

                await self.out_queue.put(
                    {"data": chunk_bytes, "mime_type": "audio/pcm"}
                )

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        while True:
            turn = self.session.receive()
            async for response in turn:
                print(response)
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

                tg.create_task(self.send_realtime())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                while True:
                    await asyncio.sleep(0.01)

        except ExceptionGroup as EG:
            traceback.print_exception(EG)


with gr.Blocks() as demo:
    audio_loop = AudioLoop()

    with gr.Row():
        interrupt_mic = gr.Button("Stop Mic")
        session_button = gr.Button("Start Session")

    # Add Gradio Audio components
    with gr.Row():
        audio_input = gr.Audio(
            sources=["microphone"], streaming=True, type="numpy", label="Input"
        )
        # audio_output = gr.Audio(
        #     type="numpy",
        #     label="Output",
        #     streaming=True,
        #     autoplay=True,
        # )

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
        return "Stop Mic" if OPEN_MIC else "Start Mic"

    interrupt_mic.click(
        toggle_mic_input,
        outputs=interrupt_mic,
    )

    # Connect audio input to processing function
    audio_input.stream(
        fn=audio_loop.process_mic_input,
        inputs=[audio_input],
    )

    # demo.load(
    #     fn=audio_loop.play_audio,
    #     outputs=[audio_output],
    # )

demo.launch()
