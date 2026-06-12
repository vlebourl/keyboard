import contextlib
import io
import json
import logging
import os
import time
import wave

import pygame
import requests
from const import COMMON_WORDS_FILE, MP3_DIR, PIPER_MODEL_PATH, PIPER_SPEAKER_JESSICA
from gtts import gTTS

_LOGGER = logging.getLogger(__name__)


class GoogleTTS:
    file_ext = "mp3"

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
                return file.getvalue()
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
    file_ext = "wav"

    def __init__(self, model_path=PIPER_MODEL_PATH, speaker_id=PIPER_SPEAKER_JESSICA):
        from piper.voice import PiperVoice  # lazy import — piper may not be installed
        self._voice = PiperVoice.load(model_path)
        self._speaker_id = speaker_id

    def set_voice(self, *_args):
        pass  # voice is fixed at load time

    def generate(self, text, retries=1):
        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                self._voice.synthesize(text, wf, speaker_id=self._speaker_id)
            return buf.getvalue()
        except Exception as e:
            _LOGGER.error("Piper TTS error for '%s': %s", text, e)
            return None


class PygameMP3Player:
    def __init__(self, tts=None):
        if not os.path.exists(MP3_DIR):
            os.makedirs(MP3_DIR)
        self.tts = tts if tts is not None else GoogleTTS()
        self.generated_words = {}
        self.word_count = {}

        self.load_common_words()

        try:
            pygame.init()
            self.player = pygame.mixer
            self.player.init()
        except pygame.error as e:
            _LOGGER.error(f"Failed to initialize Pygame audio: {e}")
            raise
        except Exception as e:
            _LOGGER.error(f"General error initializing audio: {e}")
            raise

    def preload_sound(self, text):
        filename = os.path.join(MP3_DIR, f"{text}.{self.tts.file_ext}")
        if not os.path.isfile(filename):
            audio_data = self.tts.generate(text)
            with open(filename, "wb") as f:
                f.write(audio_data)
        self.generated_words[text] = filename

    def play_mp3_file(self, filename):
        self.player.music.load(filename)
        self.player.music.play()

        while self.player.music.get_busy():
            time.sleep(0.001)

    def open_mp3_string_and_play(self, text):
        filename = self.generated_words.get(text)
        # regenerate if cached path is missing or uses a different engine's extension
        if filename is None or not os.path.isfile(filename):
            audio_data = self.tts.generate(text)
            filename = os.path.join(MP3_DIR, f"{text}.{self.tts.file_ext}")
            with open(filename, "wb") as f:
                f.write(audio_data)
            self.generated_words[text] = filename

        self.play_mp3_file(filename)

        self.word_count[text] = self.word_count.get(text, 0) + 1
        if self.word_count[text] > 2:
            self.generated_words[text] = filename

    def load_common_words(self):
        # suppress FileNotFoundError and json.decoder.JSONDecodeError
        with contextlib.suppress(FileNotFoundError, json.decoder.JSONDecodeError):
            with open(COMMON_WORDS_FILE, encoding="utf-8") as f:
                self.generated_words = json.load(f)

    def save_common_words(self):
        with open(COMMON_WORDS_FILE, "w", encoding="utf-8") as f:
            _LOGGER.info("Saving %d words", len(self.generated_words))
            json.dump(self.generated_words, f)

    def periodic_save(self, interval):
        while True:
            time.sleep(interval)
            self.save_common_words()
