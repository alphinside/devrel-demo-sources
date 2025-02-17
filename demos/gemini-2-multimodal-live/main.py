"""
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import gradio as gr
from google import genai
import asyncio
import traceback
import numpy as np
from numpy.typing import NDArray
from scipy import signal
import typer
import pyaudio
from enum import Enum
import cv2
from typing import AsyncGenerator, Optional, Tuple, Dict, Any
from settings import get_settings

app = typer.Typer()

MODEL: str = "models/gemini-2.0-flash-exp"
client: genai.Client = genai.Client(
    api_key=get_settings().GEMINI_API_KEY, http_options={"api_version": "v1alpha"}
)
CONFIG: Dict[str, Any] = {
    "generation_config": {"response_modalities": ["AUDIO"]},
    "system_instruction": (
        "Your name is Erik, always introduce yourself first before the conversation begins."
        "You are an expert in books and movies,also knowledgeable about their contents "
        "and user reviews about them.Always explain your answer in a little bit more "
        "comprehensive so that the conversation becomes more natural. DO NOT LIE and MAKE UP ANSWERS"
    ),
}
CHANNELS: int = 1
GEMINI_AUDIO_INPUT_SAMPLE_RATE: int = 16000
GEMINI_AUDIO_INPUT_CHUNK_SIZE: int = 1024
GEMINI_AUDIO_OUTPUT_SAMPLE_RATE: int = 24000
GEMINI_AUDIO_OUTPUT_CHUNK_SIZE: int = 4800
GRADIO_OUTPUT_CHUNKS_TO_COLLECT: int = 10
# send to gradio component every 10 chunks, equal to +-2 seconds of audio -> 4800 * 10 = 48000 = 2 * SAMPLE RATE
PYA: pyaudio.PyAudio = pyaudio.PyAudio()
PYA_FORMAT: int = pyaudio.paInt16
PYA_OUTPUT_CHUNK_SIZE: int = 1024


class AudioOutput(str, Enum):
    """Enum for audio output options."""

    PYAUDIO = "pyaudio"
    GRADIO = "gradio"


class MultimodalLoop:
    """
    A class that manages the multimodal interaction loop with Gemini.
    It handles audio input/output and webcam input.
    """

    def __init__(self, audio_output: AudioOutput):
        """
        Initializes the MultimodalLoop.

        Args:
            audio_output: The desired audio output method (pyaudio or gradio).
        """
        self.audio_output: AudioOutput = audio_output
        self.audio_in_queue: Optional[asyncio.Queue] = None
        self.out_queue: Optional[asyncio.Queue] = None
        self.session: Optional[genai.LiveSession] = None
        self._task: Optional[asyncio.Task] = None
        self.webcam_active: bool = False

    def resample_audio(
        self, audio_data: NDArray[np.int16], from_rate: int, to_rate: int
    ) -> NDArray[np.int16]:
        """Resample audio data from one rate to another

        Args:
            audio_data: The audio data to resample.
            from_rate: The original sample rate.
            to_rate: The desired sample rate.

        Returns:
            The resampled audio data.
        """
        if from_rate == to_rate:
            return audio_data

        # Calculate resampling ratio
        ratio: float = to_rate / from_rate

        # Calculate new length
        new_length: int = int(len(audio_data) * ratio)

        # Resample using scipy.signal.resample
        resampled: NDArray[np.float64] = signal.resample(audio_data, new_length)
        return resampled.astype(np.int16)

    async def send_realtime(self) -> None:
        """Sends messages from the output queue to the Gemini session in real-time."""
        while True:
            try:
                msg: Dict[str, Any] = self.out_queue.get_nowait()  # type: ignore
                await self.session.send(input=msg)  # type: ignore
            except Exception:
                await asyncio.sleep(0.01)

    async def process_mic_input(
        self, audio_data: Tuple[int, NDArray[np.float32]]
    ) -> None:
        """Process microphone input from Gradio

        Args:
            audio_data: A tuple containing the sample rate and audio data from Gradio.
        """
        if audio_data is not None and self.out_queue is not None:
            # Gradio returns a tuple of (sample_rate, audio_data)
            sample_rate: int
            audio_array: NDArray[np.float32]
            sample_rate, audio_array = audio_data

            # Ensure audio is mono
            if len(audio_array.shape) > 1:
                audio_array: NDArray[np.float32] = np.mean(audio_array, axis=1)

            # Resample from input rate to 16kHz
            resampled_data: NDArray[np.int16] = self.resample_audio(
                audio_array.astype(np.int16),
                sample_rate,
                GEMINI_AUDIO_INPUT_SAMPLE_RATE,
            )

            # Process audio in chunks
            num_samples: int = len(resampled_data)
            for i in range(0, num_samples, GEMINI_AUDIO_INPUT_CHUNK_SIZE):
                chunk: NDArray[np.int16] = resampled_data[
                    i : i + GEMINI_AUDIO_INPUT_CHUNK_SIZE
                ]

                # If the last chunk is smaller than CHUNK_SIZE, pad with zeros
                if len(chunk) < GEMINI_AUDIO_INPUT_CHUNK_SIZE:
                    chunk: NDArray[np.int16] = np.pad(
                        chunk,
                        (0, GEMINI_AUDIO_INPUT_CHUNK_SIZE - len(chunk)),
                        "constant",
                    ).astype(np.int16)

                # Convert chunk to bytes
                chunk_bytes: bytes = chunk.tobytes()

                await self.out_queue.put(  # type: ignore
                    {"data": chunk_bytes, "mime_type": "audio/pcm"}
                )

    async def process_webcam_frame(self, frame: NDArray[np.uint8]) -> None:
        """Process webcam frame from Gradio

        Args:
            frame: The webcam frame data from Gradio.
        """
        if frame is not None and self.session is not None:
            # Convert BGR to RGB format
            frame_rgb: NDArray[np.uint8] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Convert frame to bytes
            _, img_encoded = cv2.imencode(".jpg", frame_rgb)
            img_bytes: bytes = img_encoded.tobytes()

            await asyncio.sleep(1.0)

            # Send the frame to Gemini
            await self.out_queue.put({"data": img_bytes, "mime_type": "image/jpeg"})  # type: ignore

    async def receive_audio(self) -> None:
        """Background task to reads from the websocket and write pcm chunks to the output queue"""
        while True:
            turn = self.session.receive()  # type: ignore
            async for response in turn:
                print(response)
                if data := response.data:
                    if self.audio_output == AudioOutput.PYAUDIO:
                        self.audio_in_queue.put_nowait(data)  # type: ignore
                    elif self.audio_output == AudioOutput.GRADIO:
                        self.audio_in_queue.put_nowait(  # type: ignore
                            np.frombuffer(data, dtype=np.int16)
                        )
                    continue
                if text := response.text:
                    print(text, end="")

            # If you interrupt the model, it sends a turn_complete.
            # For interruptions to work, we need to stop playback.
            # So empty out the audio queue because it may have loaded
            # much more audio than has played yet.
            while not self.audio_in_queue.empty():  # type: ignore
                self.audio_in_queue.get_nowait()  # type: ignore

    async def play_audio_with_gradio(
        self,
    ) -> AsyncGenerator[Tuple[int, NDArray[np.int16]], None]:
        """Plays audio using Gradio's audio component.

        Yields:
            A tuple containing the sample rate and audio data.
        """
        while True:
            if self.audio_in_queue is None:
                await asyncio.sleep(0.1)
                continue

            try:
                # Wait for at least one chunk
                first_chunk: NDArray[np.int16] = await self.audio_in_queue.get()  # type: ignore
                await asyncio.sleep(0.15)  # buffer to make output smoother
                chunks: list[NDArray[np.int16]] = [first_chunk]

                # Try to get more chunks without blocking
                for _ in range(GRADIO_OUTPUT_CHUNKS_TO_COLLECT - 1):
                    await asyncio.sleep(0.15)  # buffer to make output smoother

                    try:
                        chunk: NDArray[np.int16] = self.audio_in_queue.get_nowait()  # type: ignore
                        chunks.append(chunk)
                    except asyncio.QueueEmpty:
                        break

                # Concatenate available chunks
                combined_audio: NDArray[np.int16] = np.concatenate(chunks)

                yield (GEMINI_AUDIO_OUTPUT_SAMPLE_RATE, combined_audio)

            except Exception as e:
                print(f"Error in play_audio: {e}")
                await asyncio.sleep(0.1)

    async def play_audio_with_pyaudio(self) -> None:
        """Plays audio using PyAudio."""
        stream = await asyncio.to_thread(
            PYA.open,
            format=PYA_FORMAT,
            channels=CHANNELS,
            rate=GEMINI_AUDIO_OUTPUT_SAMPLE_RATE,
            frames_per_buffer=PYA_OUTPUT_CHUNK_SIZE,
            output=True,
        )
        while True:
            bytestream: bytes = await self.audio_in_queue.get()  # type: ignore
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self) -> None:
        """Runs the main interaction loop with Gemini."""
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
) -> None:
    """
    Run the Gemini live API demo with Gradio interface.
    """
    with gr.Blocks() as demo:
        gr.Markdown("# Gemini Live API Demo")

        multimodal_loop: MultimodalLoop = MultimodalLoop(audio_output=audio_output)

        session_button: gr.Button = gr.Button("Start Session")

        # Add Gradio Audio components and Webcam components
        with gr.Row():
            audio_input: gr.Audio = gr.Audio(
                sources=["microphone"], streaming=True, type="numpy", label="Input"
            )
            audio_output_component: gr.Audio = (
                gr.Audio(label="Gemini", streaming=True, autoplay=True)
                if audio_output == AudioOutput.GRADIO
                else None
            )  # type: ignore
            webcam: gr.Image = gr.Image(
                sources=["webcam"], streaming=True, label="Webcam"
            )

        # Add text input components

        text_input: gr.Textbox = gr.Textbox(
            label="Text Message", placeholder="Type your message here...", lines=2
        )
        text_submit: gr.Button = gr.Button("Send Message")

        async def start_session(
            multimodal_loop: MultimodalLoop = multimodal_loop,
        ) -> str:
            """Starts or stops the Gemini session.

            Args:
                multimodal_loop: The MultimodalLoop instance.

            Returns:
                A string indicating the new state of the session button.
            """
            if multimodal_loop.session is None:
                multimodal_loop._task = asyncio.create_task(multimodal_loop.run())
                return "Stop Session"
            else:
                if multimodal_loop._task:
                    multimodal_loop._task.cancel()
                multimodal_loop.session = None
                return "Start Session"

        async def submit_text(
            text: str, multimodal_loop: MultimodalLoop = multimodal_loop
        ) -> str:
            """Submits text to the Gemini session.

            Args:
                text: The text to submit.
                multimodal_loop: The MultimodalLoop instance.

            Returns:
                An empty string if the text was submitted successfully, otherwise the original text.
            """
            if multimodal_loop.session and text.strip():
                await multimodal_loop.session.send(input=text, end_of_turn=True)  # type: ignore
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
                outputs=audio_output_component,  # type: ignore
            )

    demo.launch()


if __name__ == "__main__":
    app()
