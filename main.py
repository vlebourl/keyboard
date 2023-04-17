import argparse
import contextlib
import glob
import io
import json
import logging
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import alsaaudio
import pygame
import requests
from evdev import InputDevice, categorize, ecodes
from gtts import gTTS
from rpi_ws281x import Color, PixelStrip


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


def generate_color_map(key_map):
    return {
        v: [
            Color(
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
            )
            for _ in range(10)
        ]
        for v in key_map.values()
    }


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
COLOR_MAP = generate_color_map(KEY_MAP)

MP3_DIR = "sounds"
if not os.path.exists(MP3_DIR):
    os.makedirs(MP3_DIR)

# LED strip configuration:
LED_COUNT = 10  # Number of LED pixels.
LED_PIN = 18  # GPIO pin connected to the pixels (must support PWM).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10  # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53

# Create PixelStrip object
stop_green_thread = threading.Event()
led_strip = False
try:
    strip = PixelStrip(
        LED_COUNT,
        LED_PIN,
        LED_FREQ_HZ,
        LED_DMA,
        LED_INVERT,
        LED_BRIGHTNESS,
        LED_CHANNEL,
    )
    # Initialize the library
    strip.begin()
    led_strip = True
except RuntimeError:
    logging.warning("Could not initialize LED strip, skipping")

OFF = Color(0, 0, 0)
RED = Color(255, 0, 0)
WHITE = Color(255, 255, 255)
GREEN = Color(0, 255, 0)

def light_up(color):
    for i in range(strip.numPixels()):
        if isinstance(color,list):
            strip.setPixelColor(i, color[i])
        else:
            strip.setPixelColor(i, color)

def _flash(color, flash_duration_ms):
    light_up(color)
    strip.show()
    time.sleep(flash_duration_ms / 1000.0)

def flash(color=RED , num_flashes=5, flash_duration_ms=50, do_stop=True):
    if not led_strip:
        return
    if do_stop:
        global stop_green_thread  # Add this line to access the event
        stop_green_thread.set()  # Set the event to stop the green_thread
    for _ in range(num_flashes):
        _flash(color, flash_duration_ms)
        _flash(OFF, flash_duration_ms)


def light_led_i(i, color, delay):
    strip.setPixelColor(i, color)
    strip.show()
    time.sleep(delay)

def running_leds(color=GREEN, delay=0.5, stop_event=None):
    if not led_strip:
        return
    while not stop_event.is_set():
        for i in range(strip.numPixels()):
            light_led_i(i, color, delay)
        for i in range(strip.numPixels()):
            light_led_i(i, OFF, delay)


def find_keyboard_device_path():
    device_paths = glob.glob("/dev/input/by-id/*kbd*")
    if not device_paths:
        device_paths = glob.glob("/dev/input/by-id/*keyboard*")
    if not device_paths:
        flash()
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


class LEDStripContext:
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if led_strip:
            light_up(OFF)
            strip.show()

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
                    flash(RED)
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
        self.mixer.setvolume(0)
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
            if event.type != ecodes.EV_KEY:
                continue
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
                    flash(RED)
                    logging.error("Error processing key: %s", str(key_event.keycode))

    def process_letter(self, _letter: str) -> None:
        if _letter in {"\n", " ", "\r"}:
            if self.word:
                logging.info("playing word: %s", self.word)
                self.player.open_mp3_string_and_play(self.word)
                self.word = ""
            return
        if not _letter.isalnum():
            return
        logging.debug("Got letter: %s", _letter)
        logging.debug("lighting up: %s", str(COLOR_MAP[_letter]))
        light_up(COLOR_MAP[_letter])

        self.word += _letter
        self.player.open_mp3_string_and_play(f" {_letter} ")

    def loop(self):
        logging.debug("Starting main loop")
        _letter = self.get_one_letter()
        while True:
            try:
                self.process_letter(_letter)
                _letter = self.get_one_letter()
            except Exception as e:
                flash(RED)
                logging.error("Critical Exception: %s", e)


if __name__ == "__main__":
    with LEDStripContext():
        flash(WHITE, do_stop=False)
        logging.info("Starting talking keyboard")
        green_thread = threading.Thread(
            target=running_leds, args=(GREEN,0.1, stop_green_thread), daemon=True
        )
        green_thread.start()
        time.sleep(2)

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

        light_up(OFF)
        flash(GREEN)
        keyboard.loop()
