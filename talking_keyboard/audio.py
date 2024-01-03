import contextlib
import io
import json
import logging
import os
import time

import alsaaudio
import pygame
import requests
from gtts import gTTS

from const import COMMON_WORDS_FILE, MP3_DIR

_LOGGER = logging.getLogger(__name__)


class AlsaMixer:
    def __init__(self, mixer_name="PCM", cardindex=1):
        self.mixer = alsaaudio.Mixer("PCM", cardindex=3)
        self.volume = self.getvolume()
    
    def getvolume(self):
        return self.mixer.getvolume()[0]

    def set_volume(self, vol):
        self.mixer.setvolume(vol)
        _LOGGER.info("Volume set to %d", vol)


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


class PygameMP3Player:
    def __init__(self, tts):
        if not os.path.exists(MP3_DIR):
            os.makedirs(MP3_DIR)
        self.tts = tts
        self.generated_words = {}
        self.word_count = {}

        self.load_common_words()

        try:
            # Check if audio devices are available
            if len(alsaaudio.cards()) == 0:
                raise Exception("No ALSA audio devices found.")

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
        filename = os.path.join(MP3_DIR, f"{text}.mp3")
        if not os.path.isfile(filename):
            mp3_data = self.tts.generate(text)
            with open(filename, "wb") as f:
                f.write(mp3_data)
        self.generated_words[text] = filename

    def play_mp3_file(self, filename):
        self.player.music.load(filename)
        self.player.music.play()

        while self.player.music.get_busy():
            time.sleep(0.001)

    def open_mp3_string_and_play(self, text):
        filename = self.generated_words.get(text, None)
        if filename is None:
            mp3_data = self.tts.generate(text)
            filename = os.path.join(MP3_DIR, f"{text}.mp3")
            with open(filename, "wb") as f:
                f.write(mp3_data)
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
