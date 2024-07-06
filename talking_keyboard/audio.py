import logging
import os
from urllib.request import urlretrieve

import numpy as np
import sounddevice as sd
from piper.voice import PiperVoice

_LOGGER = logging.getLogger(__name__)


class PiperTTS:
    def __init__(self, path: str, model: str):
        if not os.path.exists(path):
            os.makedirs(path)
        if not os.path.exists(f"{path}/{model}.onnx.json"):
            _LOGGER.info(f"Downloading model {model} from huggingface.co")
            urlretrieve(
                f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{model[:2]}/{model.replace('-', '/')}/{model}.onnx.json",
                f"{path}/{model}.onnx.json",
            )  # nosec
            urlretrieve(
                f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{model[:2]}/{model.replace('-', '/')}/{model}.onnx",
                f"{path}/{model}.onnx",
            )  # nosec

        self.voice = PiperVoice.load(f"{path}/{model}.onnx")

    @property
    def sample_rate(self):
        return self.voice.config.sample_rate

    def generate(self, text):
        return self.voice.synthesize_stream_raw(text)


class Streamer:
    def __init__(self, path: str):
        self.voice = PiperTTS(path, "fr_FR-siwis-medium")
        self.stream = sd.OutputStream(
            samplerate=self.voice.sample_rate, channels=1, dtype="int16"
        )

    # destructor, use stream.close()
    def __del__(self):
        self.stream.close()

    def play(self, text):
        self.stream.start()
        for audio_bytes in self.voice.generate(text):
            int_data = None
            int_data = np.frombuffer(audio_bytes, dtype=np.int16)
            self.stream.write(int_data)
        self.stream.stop()
