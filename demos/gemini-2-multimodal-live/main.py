import gradio as gr
import numpy as np
import librosa

INPUT_SAMPLE_RATE = 16000


class StreamingLoop:
    def __init__(self):
        self.audio_in_queue = []


def transcribe(new_chunk):
    sr, y = new_chunk
    # Convert to float32
    y = y.astype(np.float32)
    # Resample to 16000 Hz
    y_resampled = librosa.resample(y=y, orig_sr=sr, target_sr=INPUT_SAMPLE_RATE)

    return (INPUT_SAMPLE_RATE, y_resampled)


demo = gr.Interface(
    transcribe,
    [gr.Audio(sources=["microphone"], streaming=True, every=1)],
    [gr.Audio(streaming=True, autoplay=True)],
    live=True,
)

demo.launch()
