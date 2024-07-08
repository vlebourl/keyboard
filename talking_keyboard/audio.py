import io
import logging
import os

import numpy as np
import requests
import sounddevice as sd
from gtts import gTTS
from piper.voice import PiperVoice

_LOGGER = logging.getLogger(__name__)


def check_internet(url="http://www.google.com", timeout=3):
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.ConnectionError as ex:
        print(f"Error: {ex}")
        return False


def download_file(url, local_path):
    try:
        with requests.get(url, stream=True, timeout=5) as response:
            response.raise_for_status()
            with open(local_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
    except Exception as e:
        _LOGGER.error(f"Failed to download {url}. Error: {e}")
        raise


class GoogleTTS:
    def __init__(self, language="fr"):
        self._language = language[:2]

    def set_voice(self, language):
        self._language = language[:2]

    def generate(self, text, retries=3):
        for i in range(retries):
            try:
                tts = gTTS(text=text, lang=self._language)
                file = io.BytesIO()
                tts.write_to_fp(file)
                file.seek(0)
                return file.read()
            except (requests.exceptions.RequestException, Exception) as e:
                _LOGGER.error("Error generating TTS for text '%s': %s", text, e)
                if i < retries - 1:
                    _LOGGER.info("Retrying (%d/%d)...", i + 1, retries)
                else:
                    _LOGGER.error(
                        "Failed to generate TTS for text '%s' after %d retries",
                        text,
                        retries,
                    )
                    return None
        return None


class PiperTTS:
    def __init__(self, path: str = "models", model: str = "fr_FR-siwis-medium"):
        if not os.path.exists(path):
            os.makedirs(path)
        if not os.path.exists(f"{path}/{model}.onnx.json"):
            _LOGGER.info(f"Downloading model {model} from huggingface.co")
            base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
            model_url_base = f"{base_url}/{model[:2]}/{model.replace('-', '/')}"
            download_file(
                f"{model_url_base}/{model}.onnx.json", f"{path}/{model}.onnx.json"
            )
            download_file(f"{model_url_base}/{model}.onnx", f"{path}/{model}.onnx")

        self.voice = PiperVoice.load(f"{path}/{model}.onnx")

    def get_sample_rate(self):
        return self.voice.config.sample_rate

    def generate(self, text):
        return self.voice.synthesize_stream_raw(text)


class Streamer:
    def __init__(self, sample_rate=22050):
        if check_internet():
            self.tts = GoogleTTS("fr")
            self._sample_rate = sample_rate
        else:
            self.tts = PiperTTS("models", "next")
            self._sample_rate = self.tts.get_sample_rate()
        self.stream = sd.OutputStream(
            samplerate=self._sample_rate, channels=1, dtype="int16"
        )

    # Destructor, use stream.close()
    def __del__(self):
        self.stream.close()

    def play(self, text):
        self.stream.start()
        if generated := self.tts.generate(text):
            if isinstance(generated, bytes):  # GoogleTTS case
                int_data = np.frombuffer(generated, dtype=np.int16)
                self.stream.write(int_data)
            else:  # PiperTTS case
                for audio_bytes in generated:
                    int_data = np.frombuffer(audio_bytes, dtype=np.int16)
                    self.stream.write(int_data)
        self.stream.stop()
