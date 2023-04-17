import argparse
import contextlib
import glob
import io
import json
import logging
import os
import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import alsaaudio
import pygame
from evdev import InputDevice, categorize, ecodes
from gtts import gTTS


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Talking keyboard with adjustable logging level"
    )
    parser.add_argument(
        "--loglevel",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: %(default))",
    )
    return parser.parse_args()


args = parse_arguments()
numeric_level = getattr(logging, args.loglevel.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {args.loglevel}")


logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

VOICES = ["de-DE", "en-GB", "en-US", "es-ES", "fr-FR", "it-IT"]

COMMON_WORDS_FILE = "common_words.json"
COMMON_LETTERS = "abcdefghijklmnopqrstuvwxyz1234567890"
KEY_MAP = {
    "KEY_A": "q",
    "KEY_B": "b",
    "KEY_C": "c",
    "KEY_D": "d",
    "KEY_E": "e",
    "KEY_F": "f",
    "KEY_G": "g",
    "KEY_H": "h",
    "KEY_I": "i",
    "KEY_J": "j",
    "KEY_K": "k",
    "KEY_L": "l",
    "KEY_N": "n",
    "KEY_O": "o",
    "KEY_P": "p",
    "KEY_Q": "a",
    "KEY_R": "r",
    "KEY_S": "s",
    "KEY_T": "t",
    "KEY_U": "u",
    "KEY_V": "v",
    "KEY_W": "z",
    "KEY_X": "x",
    "KEY_Y": "y",
    "KEY_Z": "w",
    "KEY_0": "0",
    "KEY_1": "1",
    "KEY_2": "2",
    "KEY_3": "3",
    "KEY_4": "4",
    "KEY_5": "5",
    "KEY_6": "6",
    "KEY_7": "7",
    "KEY_8": "8",
    "KEY_9": "9",
    "KEY_SEMICOLON": "m",
    "KEY_SPACE": " ",
    "KEY_ENTER": "\n",
    "KEY_BACKSPACE": "\b",
    "KEY_TAB": "\t",
    "KEY_KPENTER": "\n",
    "KEY_KP0": "0",
    "KEY_KP1": "1",
    "KEY_KP2": "2",
    "KEY_KP3": "3",
    "KEY_KP4": "4",
    "KEY_KP5": "5",
    "KEY_KP6": "6",
    "KEY_KP7": "7",
    "KEY_KP8": "8",
    "KEY_KP9": "9",
    # Add other keys as needed
}

MP3_DIR = "sounds"
if not os.path.exists(MP3_DIR):
    os.makedirs(MP3_DIR)


def find_keyboard_device_path():
    device_paths = glob.glob("/dev/input/by-id/*kbd*")
    if not device_paths:
        device_paths = glob.glob("/dev/input/by-id/*keyboard*")
    if not device_paths:
        raise ValueError("No keyboard device found!")

    if len(device_paths) == 1:
        return device_paths[0]
    logging.warn("Multiple keyboard devices found:")
    for i, device_path in enumerate(device_paths, start=0):
        logging.warn("[%d]: %s", i, device_path)
    logging.warn("Using [0]: %s", device_paths[0])
    return device_paths[0]


def preload_sounds_parallel(_keyboard, _letters):
    with ThreadPoolExecutor() as executor:
        executor.map(_keyboard.player.preload_sound, _letters)


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
                logging.error("Error generating TTS for text '%s': %s", text, e)
                if i < retries - 1:
                    logging.info("Retrying (%d/%d)...", i + 1, retries)
                else:
                    logging.error(
                        "Failed to generate TTS for text '%s' after %d retries",
                        text,
                        retries,
                    )
                    return None
        return None


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
            logging.info("Saving %d words", len(self.generated_words))
            json.dump(self.generated_words, f)

    def periodic_save(self, interval):
        while True:
            time.sleep(interval)
            self.save_common_words()


class Keyboard:
    def __init__(self, device_path=None):
        if device_path is None:
            device_path = find_keyboard_device_path()
        self.device = InputDevice(device_path)
        self.mixer = alsaaudio.Mixer("PCM", cardindex=1)
        self.volume = self.mixer.getvolume()[0]
        self.mixer.setvolume(90)
        self.tts = GoogleTTS()
        self.player = PygameMP3Player(self.tts)
        self.word = ""
        self.shift_pressed = False
        self.caps_lock = False

    def set_volume(self, vol):
        self.mixer.setvolume(vol)
        logging.info("Volume set to %d", vol)

    def update_key_states(self, key_event):
        if key_event.keycode in ["KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"]:
            self.shift_pressed = key_event.keystate == key_event.key_down
        elif (
            key_event.keycode == "KEY_CAPSLOCK"
            and key_event.keystate == key_event.key_down
        ):
            self.caps_lock = not self.caps_lock

    def get_one_letter(self):
        for event in self.device.read_loop():
            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                self.update_key_states(key_event)
                if key_event.keystate == key_event.key_up:
                    try:
                        if mapped_key := KEY_MAP.get(
                            key_event.keycode[0]
                            if isinstance(key_event.keycode, list)
                            else key_event.keycode,
                            "",
                        ):
                            if mapped_key.isalpha() and (
                                self.shift_pressed != self.caps_lock
                            ):
                                mapped_key = mapped_key.upper()
                            return mapped_key
                        elif key_event.keycode == "KEY_VOLUMEUP":
                            self.set_volume(min(self.mixer.getvolume()[0] + 5, 100))
                        elif key_event.keycode == "KEY_VOLUMEDOWN":
                            self.set_volume(min(self.mixer.getvolume()[0] - 5, 100))
                        elif (
                            isinstance(key_event.keycode, list)
                            and key_event.keycode[0] == "KEY_MIN_INTERESTING"
                        ):
                            if self.mixer.getvolume()[0] > 0:
                                self.volume = self.mixer.getvolume()[0]
                                self.set_volume(0)
                            else:
                                self.set_volume(self.volume)
                        else:
                            logging.warning("Unsupported key: %s", key_event.keycode)
                    except TypeError:
                        logging.error(
                            "Error processing key: %s", str(key_event.keycode)
                        )

    def process_letter(self, _letter: str) -> None:
        if _letter in {"\n", " ", "\r"}:
            if self.word:
                logging.info("playing word: %s", self.word)
                self.player.open_mp3_string_and_play(self.word)
                self.word = ""
            return
        if not _letter.isalnum():
            return
        self.word += _letter
        self.player.open_mp3_string_and_play(f" {_letter} ")

    def loop(self):
        _letter = self.get_one_letter()
        while True:
            try:
                self.process_letter(_letter)
                _letter = self.get_one_letter()
            except Exception as e:
                logging.error("Critical Exception: %s", e)


if __name__ == "__main__":
    logging.info("Starting talking keyboard")

    keyboard = Keyboard()

    logging.info("Preloading common letters")
    for letter in COMMON_LETTERS:
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
