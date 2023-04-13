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
from evdev import InputDevice, categorize, ecodes

import pygame
from gtts import gTTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

VOICES = ["de-DE", "en-GB", "en-US", "es-ES", "fr-FR", "it-IT"]

COMMON_WORDS_FILE = "common_words.json"

AZERTY_KEY_MAP = {
    'KEY_A': 'q',
    'KEY_B': 'b',
    'KEY_C': 'c',
    'KEY_D': 'd',
    'KEY_E': 'e',
    'KEY_F': 'f',
    'KEY_G': 'g',
    'KEY_H': 'h',
    'KEY_I': 'i',
    'KEY_J': 'j',
    'KEY_K': 'k',
    'KEY_L': 'l',
    'KEY_N': 'n',
    'KEY_O': 'o',
    'KEY_P': 'p',
    'KEY_Q': 'a',
    'KEY_R': 'r',
    'KEY_S': 's',
    'KEY_T': 't',
    'KEY_U': 'u',
    'KEY_V': 'v',
    'KEY_W': 'z',
    'KEY_X': 'x',
    'KEY_Y': 'y',
    'KEY_Z': 'w',
    'KEY_0': '0',
    'KEY_1': '1',
    'KEY_2': '2',
    'KEY_3': '3',
    'KEY_4': "4",
    'KEY_5': '5',
    'KEY_6': '6',
    'KEY_7': '7',
    'KEY_8': '8',
    'KEY_9': '9',
    'KEY_SEMICOLON': 'm',
    'KEY_SPACE': ' ',
    'KEY_ENTER': '\n',
    'KEY_BACKSPACE': '\b',
    'KEY_TAB': '\t',
    'KEY_KPENTER': '\n',
    'KEY_KP0': '0',
    'KEY_KP1': '1',
    'KEY_KP2': '2',
    'KEY_KP3': '3',
    'KEY_KP4': '4',
    'KEY_KP5': '5',
    'KEY_KP6': '6',
    'KEY_KP7': '7',
    'KEY_KP8': '8',
    'KEY_KP9': '9',
    # Add other keys as needed
}

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
        # suppress FileNotFoundError and json.decoder.JSONDecodeError
        with contextlib.suppress(FileNotFoundError, json.decoder.JSONDecodeError):
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
    def __init__(self, device_path="/dev/input/by-id/usb-Logitech_USB_Receiver-if02-event-kbd"):
        self.device = InputDevice(device_path)
        self.key_map = self.create_key_map()
        self.tts = GoogleTTS()
        self.player = PygameMP3Player(self.tts)
        self.word = ""

    def get_one_letter(self):
        for event in self.device.read_loop():
            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                if key_event.keystate == key_event.key_up:
                    keycode = key_event.keycode
                    logging.info(f"received: {keycode}")
                    return self.key_map.get(keycode,"")

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
