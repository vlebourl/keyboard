import contextlib
import io
import pickle
import socket
import subprocess
import sys
import tempfile
import termios
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import simpleaudio as sa
from gtts import gTTS

VOICES = ["de-DE", "en-GB", "en-US", "es-ES", "fr-FR", "it-IT"]

COMMON_WORDS_FILE = "common_words.pickle"


def preload_sounds_parallel(keyboard, letters):
    with ThreadPoolExecutor() as executor:
        executor.map(keyboard.player.preload_sound, letters)


class PicoTTS:
    def __init__(self, voice="en-US"):
        self._voice = voice

    def generate(self, txt):
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            args = ["pico2wave", "-l", self._voice, "-w", f.name, txt]
            subprocess.run(args, check=True)
            f.seek(0)
            wav = f.read()
        return wav

    def set_voice(self, v):
        self._voice = v


class GoogleTTS:
    def __init__(self, language="fr"):
        self._language = language[:2]

    def set_voice(self, language):
        self._language = language[:2]

    def generate(self, text):
        tts = gTTS(text=text, lang=self._language)
        file = io.BytesIO()
        tts.write_to_fp(file)
        return file.getvalue()


class TTS:
    def __init__(self, internet=False, language="fr-FR"):
        self.tts = GoogleTTS(language) if internet else PicoTTS(language)

    def generate(self, text):
        return self.tts.generate(text)


class WavePlayer:
    def __init__(self, tts, internet=False):
        self.tts = tts
        self._internet = internet
        self.generated_words = {}
        self.word_count = {}

        if internet:
            self.load_common_words()

    def preload_sound(self, text):
        wav = self.tts.generate(text)
        wave_obj = sa.WaveObject.from_wave_file(io.BytesIO(wav))
        self.generated_words[text] = wave_obj

    def open_wave_string_and_play(self, text, wave_string=None):
        if text in self.generated_words:
            wave_obj = self.generated_words[text]
        else:
            if wave_string is None:
                wave_string = self.tts.generate(text)
            wave_obj = sa.WaveObject.from_wave_file(io.BytesIO(wave_string))
            self.generated_words[text] = wave_obj
        wave_obj.play()

        self.word_count[text] = self.word_count.get(text, 0) + 1
        if self.word_count[text] >= 2:
            self.generated_words[text] = wave_obj

    def load_common_words(self):
        with contextlib.suppress(FileNotFoundError):
            with open(COMMON_WORDS_FILE, "rb") as f:
                self.generated_words = pickle.load(f)

    def save_common_words(self):
        with open(COMMON_WORDS_FILE, "wb") as f:
            pickle.dump(self.generated_words, f)

    def periodic_save(self, interval):
        while True:
            time.sleep(interval)
            self.save_common_words()


class Keyboard:
    def __init__(self, internet=False):
        self.tts = TTS(internet)
        self.player = WavePlayer(self.tts, internet)
        self.word = ""

    def get_one_letter(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            new_settings = termios.tcgetattr(fd)
            new_settings[3] = new_settings[3] & ~termios.ICANON & ~termios.ECHO
            termios.tcsetattr(fd, termios.TCSAFLUSH, new_settings)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def process_letter(self, letter: str) -> None:
        if letter in {"\n", " ", "\r"}:
            if self.word:
                self.player.open_wave_string_and_play(
                    self.word
                )  # Pass the word without the wave_string
                self.word = ""
            return
        if not letter.isalnum():
            return
        self.word += letter
        self.player.open_wave_string_and_play(f" {letter} ")

    def loop(self):
        letter = self.get_one_letter()
        while True:
            self.process_letter(letter)
            letter = self.get_one_letter()


if __name__ == "__main__":
    internet = False
    with contextlib.suppress(Exception):
        host = socket.gethostbyname("www.google.com")
        socket.create_connection((host, 80), 2)
        internet = True

    keyboard = Keyboard(internet)

    # Preload most common letters
    common_letters = "abcdefghijklmnopqrstuvwxyz1234567890"
    for letter in common_letters:
        if f" {letter} " not in keyboard.player.generated_words:
            keyboard.player.preload_sound(f" {letter} ")

    keyboard.word = "Bonjour, bienvenue sur le clavier parlant."

    if internet:
        keyboard.word += " Internet actif."
    keyboard.process_letter("\n")

    # Launch a new thread to periodically save common words
    save_thread = threading.Thread(
        target=keyboard.player.periodic_save, args=(300,), daemon=True
    )
    save_thread.start()

    keyboard.loop()
