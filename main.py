import contextlib
import io
import json
import logging
import sys
import tempfile
import termios
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pygame
from gtts import gTTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

VOICES = ["de-DE", "en-GB", "en-US", "es-ES", "fr-FR", "it-IT"]

COMMON_WORDS_FILE = "common_words.json"


def preload_sounds_parallel(keyboard, letters):
    with ThreadPoolExecutor() as executor:
        executor.map(keyboard.player.preload_sound, letters)


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


class PygameMP3Player:
    def __init__(self, tts):
        self.tts = tts
        self.generated_words = {}
        self.word_count = {}

        self.load_common_words()

        pygame.init()
        self.player = pygame.mixer
        self.player.init()

    def preload_sound(self, text):
        mp3_data = self.tts.generate(text)
        self.generated_words[text] = mp3_data

    def play_mp3_data(self, mp3_data):
        with tempfile.NamedTemporaryFile(delete=True) as f:
            f.write(mp3_data)
            f.flush()

            self.player.music.load(f.name)
            self.player.music.play()

            while self.player.music.get_busy():
                time.sleep(0.001)

    def open_mp3_string_and_play(self, text, mp3_data=None):
        mp3_data = self.generated_words.get(text, None)
        if mp3_data is None:
            mp3_data = self.tts.generate(text)

        self.play_mp3_data(mp3_data)

        self.word_count[text] = self.word_count.get(text, 0) + 1
        if self.word_count[text] > 2:
            self.generated_words[text] = mp3_data

    def load_common_words(self):
        with contextlib.suppress(FileNotFoundError):
            with open(COMMON_WORDS_FILE, "r") as f:
                self.generated_words = {
                    k: bytes.fromhex(v) for k, v in json.load(f).items()
                }

    def save_common_words(self):
        with open(COMMON_WORDS_FILE, "w") as f:
            logging.info("Saving %d words", len(self.generated_words))
            json.dump({k: v.hex() for k, v in self.generated_words.items()}, f)

    def periodic_save(self, interval):
        while True:
            time.sleep(interval)
            self.save_common_words()


class Keyboard:
    def __init__(self):
        self.tts = GoogleTTS()
        self.player = PygameMP3Player(self.tts)
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
                logging.info("playing word: %s", self.word)
                self.player.open_mp3_string_and_play(self.word)
                self.word = ""
            return
        if not letter.isalnum():
            return
        self.word += letter
        self.player.open_mp3_string_and_play(f" {letter} ")

    def loop(self):
        letter = self.get_one_letter()
        while True:
            self.process_letter(letter)
            letter = self.get_one_letter()


if __name__ == "__main__":
    logging.info("Starting talking keyboard")

    keyboard = Keyboard()

    common_letters = "abcdefghijklmnopqrstuvwxyz1234567890"
    logging.info("Preloading common letters")
    for letter in common_letters:
        if f" {letter} " not in keyboard.player.generated_words:
            logging.info("    Preloading letter: %s", letter)
            keyboard.player.preload_sound(f" {letter} ")
    keyboard.player.save_common_words()

    logging.info("Preloaded words are:")
    for word in keyboard.player.generated_words.keys():
        logging.info("    %s", word)

    keyboard.word = "Bonjour, bienvenue sur le clavier parlant."
    keyboard.process_letter("\n")

    save_thread = threading.Thread(
        target=keyboard.player.periodic_save, args=(300,), daemon=True
    )
    save_thread.start()

    keyboard.loop()
