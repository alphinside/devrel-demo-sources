import gradio as gr
from google import genai
import asyncio
import traceback
import numpy as np
from scipy import signal
import typer
import pyaudio
from enum import Enum
import cv2


app = typer.Typer()

MODEL = "models/gemini-2.0-flash-exp"
client = genai.Client(http_options={"api_version": "v1alpha"})
CONFIG = {
    "generation_config": {"response_modalities": ["AUDIO"]},
    "system_instruction": (
        "Your name is Erik, always introduce yourself first before the conversation begins."
        "You are an expert in product management and can suggest best practices "
        "how to design and launch a successful product. Always explain your answer in a "
        "little bit more comprehensive so that the conversation becomes more natural."
        "DO NOT LIE and MAKE UP ANSWERS"
    ),
}
CHANNELS = 1
GEMINI_AUDIO_INPUT_SAMPLE_RATE = 16000
GEMINI_AUDIO_INPUT_CHUNK_SIZE = 1024
GEMINI_AUDIO_OUTPUT_SAMPLE_RATE = 24000
GEMINI_AUDIO_OUTPUT_CHUNK_SIZE = 4800
GRADIO_OUTPUT_CHUNKS_TO_COLLECT = 10
# send to gradio component every 10 chunks, equal to +-2 seconds of audio -> 4800 * 10 = 48000 = 2 * SAMPLE RATE
PYA = pyaudio.PyAudio()
PYA_FORMAT = pyaudio.paInt16
PYA_OUTPUT_CHUNK_SIZE = 1024


class AudioOutput(str, Enum):
    """Enum for audio output options."""

    PYAUDIO = "pyaudio"
    GRADIO = "gradio"


class MultimodalLoop:
    def __init__(self, audio_output: AudioOutput):
        self.audio_output = audio_output
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self._task = None
        self.webcam_active = False

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

    async def send_realtime(self):
        while True:
            try:
                msg = self.out_queue.get_nowait()

                await self.session.send(input=msg)
            except Exception:
                await asyncio.sleep(0.01)

    async def process_mic_input(self, audio_data):
        """Process microphone input from Gradio"""

        if audio_data is not None and self.out_queue is not None:
            # Gradio returns a tuple of (sample_rate, audio_data)
            sample_rate, audio_array = audio_data

            # Ensure audio is mono
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)

            # Resample from input rate to 16kHz
            resampled_data = self.resample_audio(
                audio_array, sample_rate, GEMINI_AUDIO_INPUT_SAMPLE_RATE
            )

            # Process audio in chunks
            num_samples = len(resampled_data)
            for i in range(0, num_samples, GEMINI_AUDIO_INPUT_CHUNK_SIZE):
                chunk = resampled_data[i : i + GEMINI_AUDIO_INPUT_CHUNK_SIZE]

                # If the last chunk is smaller than CHUNK_SIZE, pad with zeros
                if len(chunk) < GEMINI_AUDIO_INPUT_CHUNK_SIZE:
                    chunk = np.pad(
                        chunk,
                        (0, GEMINI_AUDIO_INPUT_CHUNK_SIZE - len(chunk)),
                        "constant",
                    )

                # Convert chunk to bytes
                chunk_bytes = chunk.tobytes()

                await self.out_queue.put(
                    {"data": chunk_bytes, "mime_type": "audio/pcm"}
                )

    async def process_webcam_frame(self, frame):
        """Process webcam frame from Gradio"""
        if frame is not None and self.session is not None:
            # Convert BGR to RGB format
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert frame to bytes
            _, img_encoded = cv2.imencode(".jpg", frame_rgb)
            img_bytes = img_encoded.tobytes()

            await asyncio.sleep(1.0)

            # Send the frame to Gemini
            await self.out_queue.put({"data": img_bytes, "mime_type": "image/jpeg"})

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        while True:
            turn = self.session.receive()
            async for response in turn:
                print(response)
                if data := response.data:
                    if self.audio_output == AudioOutput.PYAUDIO:
                        self.audio_in_queue.put_nowait(data)
                    elif self.audio_output == AudioOutput.GRADIO:
                        self.audio_in_queue.put_nowait(
                            np.frombuffer(data, dtype=np.int16)
                        )
                    continue
                if text := response.text:
                    print(text, end="")

            # If you interrupt the model, it sends a turn_complete.
            # For interruptions to work, we need to stop playback.
            # So empty out the audio queue because it may have loaded
            # much more audio than has played yet.
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()

    async def play_audio_with_gradio(self):
        while True:
            if self.audio_in_queue is None:
                await asyncio.sleep(0.1)
                continue

            try:
                # Wait for at least one chunk
                first_chunk = await self.audio_in_queue.get()
                await asyncio.sleep(0.15)  # buffer to make output smoother
                chunks = [first_chunk]

                # Try to get more chunks without blocking
                for _ in range(GRADIO_OUTPUT_CHUNKS_TO_COLLECT - 1):
                    await asyncio.sleep(0.15)  # buffer to make output smoother

                    try:
                        chunk = self.audio_in_queue.get_nowait()
                        chunks.append(chunk)
                    except asyncio.QueueEmpty:
                        break

                # Concatenate available chunks
                combined_audio = np.concatenate(chunks)

                yield (GEMINI_AUDIO_OUTPUT_SAMPLE_RATE, combined_audio)

            except Exception as e:
                print(f"Error in play_audio: {e}")
                await asyncio.sleep(0.1)

    async def play_audio_with_pyaudio(self):
        stream = await asyncio.to_thread(
            PYA.open,
            format=PYA_FORMAT,
            channels=CHANNELS,
            rate=GEMINI_AUDIO_OUTPUT_SAMPLE_RATE,
            frames_per_buffer=PYA_OUTPUT_CHUNK_SIZE,
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

                if self.audio_output == AudioOutput.PYAUDIO:
                    tg.create_task(self.play_audio_with_pyaudio())

                while True:
                    await asyncio.sleep(0.01)

        except ExceptionGroup as EG:
            traceback.print_exception(EG)


@app.command()
def main(
    audio_output: AudioOutput = AudioOutput.PYAUDIO,
):
    """
    Run the Gemini live API demo with Gradio interface.
    """
    with gr.Blocks() as demo:
        gr.Markdown("# Gemini Live API Demo")

        multimodal_loop = MultimodalLoop(audio_output=audio_output)

        session_button = gr.Button("Start Session")

        # Add Gradio Audio components and Webcam components
        with gr.Row():
            audio_input = gr.Audio(
                sources=["microphone"], streaming=True, type="numpy", label="Input"
            )
            if audio_output == AudioOutput.GRADIO:
                audio_output = gr.Audio(label="Gemini", streaming=True, autoplay=True)
            webcam = gr.Image(sources=["webcam"], streaming=True, label="Webcam")

        # Add text input components

        text_input = gr.Textbox(
            label="Text Message", placeholder="Type your message here...", lines=2
        )
        text_submit = gr.Button("Send Message")

        async def start_session(multimodal_loop=multimodal_loop):
            if multimodal_loop.session is None:
                multimodal_loop._task = asyncio.create_task(multimodal_loop.run())
                return "Stop Session"
            else:
                if multimodal_loop._task:
                    multimodal_loop._task.cancel()
                multimodal_loop.session = None
                return "Start Session"

        async def submit_text(text, multimodal_loop=multimodal_loop):
            if multimodal_loop.session and text.strip():
                await multimodal_loop.session.send(input=text, end_of_turn=True)
                return ""  # Clear the textbox after sending
            return text  # Keep the text if session is not active

        session_button.click(
            start_session,
            outputs=session_button,
        )

        # Connect audio input to processing function
        audio_input.stream(
            fn=multimodal_loop.process_mic_input,
            inputs=[audio_input],
        )

        # Connect webcam input to processing function
        webcam.stream(
            fn=multimodal_loop.process_webcam_frame,
            inputs=[webcam],
        )

        # Connect text input to submit functio
        text_submit.click(
            fn=submit_text,
            inputs=[text_input],
            outputs=[text_input],
        )

        # Connect audio output to play_audio function
        if audio_output == AudioOutput.GRADIO:
            demo.load(
                multimodal_loop.play_audio_with_gradio,
                outputs=audio_output,
            )

    demo.launch()


if __name__ == "__main__":
    app()
