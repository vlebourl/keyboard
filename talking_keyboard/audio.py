import logging
import os
from urllib.request import urlretrieve

import numpy as np
import sounddevice as sd
from const import MODEL_DIR
from piper.voice import PiperVoice

_LOGGER = logging.getLogger(__name__)


class PiperTTS:
    def __init__(self, model: str):
        if not os.path.exists(MODEL_DIR):
            os.makedirs(MODEL_DIR)
        if not os.path.exists(f"{MODEL_DIR}/{model}.onnx.json"):
            _LOGGER.info(f"Downloading model {model} from huggingface.co")
            urlretrieve(
                f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{model[:2]}/{model.replace('-', '/')}/{model}.onnx.json",
                f"{MODEL_DIR}/{model}.onnx.json",
            )  # nosec
            urlretrieve(
                f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{model[:2]}/{model.replace('-', '/')}/{model}.onnx",
                f"{MODEL_DIR}/{model}.onnx",
            )  # nosec

        self.voice = PiperVoice.load(model)

    @property
    def sample_rate(self):
        return self.voice.config.sample_rate

    def generate(self, text):
        return self.voice.synthesize_stream_raw(text)


class Streamer:
    def __init__(self):
        self.voice = PiperTTS("fr_FR-siwis-medium")
        self.stream = sd.OutputStream(
            samplerate=self.voice.sample_rate, channels=1, dtype="int16"
        )

    # destructor, use stream.close()
    def __del__(self):
        self.stream.close()

    def play(self, text):
        self.stream.start()
        for audio_bytes in self.voice.generate(text):
            int_data = np.frombuffer(audio_bytes, dtype=np.int16)
            self.stream.write(int_data)
        self.stream.stop()
