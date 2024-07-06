import logging
import os
from urllib.request import urlretrieve

import numpy as np
import sounddevice as sd
from piper.voice import PiperVoice

_LOGGER = logging.getLogger(__name__)


class Streamer:

    stream = None
    voice = None

    def __init__(self, path: str = "models", model: str = "fr_FR-siwis-medium"):

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

    # destructor, use stream.close()
    def __del__(self):
        self.stream.close()

    def generate(self, text):
        return self.voice.synthesize_stream_raw(text)

    def _open_stream(self):
        if self.stream is not None:
            self.stream.close()
        self.stream = sd.OutputStream(
            samplerate=self.voice.config.sample_rate, channels=1, dtype="int16"
        )

    def play(self, text):
        self._open_stream()  # Ensure the stream is reopened before each play call
        self.stream.start()
        generated = self.generate(text)
        for audio_bytes in generated:
            int_data = None
            int_data = np.frombuffer(audio_bytes, dtype=np.int16)
            self.stream.write(int_data)
        self.stream.stop()
