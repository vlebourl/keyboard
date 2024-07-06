import glob
import logging
import sys

from evdev import InputDevice, categorize, ecodes
from num2words import num2words
import re
from .audio import PiperTTS, Streamer
from .const import KEY_MAP

_LOGGER = logging.getLogger(__name__)


def split_alpha_num(word):
    # Regular expression to match sequences of letters or digits
    return re.findall(r'[A-Za-z]+|\d+', word)

class Keyboard:
    def __init__(self, lcd):
        _device_paths = glob.glob("/dev/input/by-id/*kbd*") or glob.glob("/dev/input/by-id/*ogitech*")
        if not _device_paths:
            raise ValueError("No keyboard device found!")
        self.device = InputDevice(_device_paths[0])
        self.streamer = Streamer()

        self.word = ""
        self.shift_pressed = False
        self.caps_lock = False
        self.lcd = lcd

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
                        return mapped_key
                  #  elif key_event.keycode == "KEY_VOLUMEUP":
                  #      self.mixer.set_volume(min(self.mixer.getvolume() + 5, 100))
                  #      self.lcd.write_words(f"Volume up: {self.mixer.getvolume()}", self.lcd.get_buffer()[1])
                  #  elif key_event.keycode == "KEY_VOLUMEDOWN":
                  #      self.mixer.set_volume(min(self.mixer.getvolume() - 5, 100))
                  #      self.lcd.write_words(f"Volume down: {self.mixer.getvolume()}", self.lcd.get_buffer()[1])
                  #  elif (
                  #      isinstance(key_event.keycode, list)
                  #      and key_event.keycode[0] == "KEY_MIN_INTERESTING"
                  #  ):
                  #      if self.mixer.mixer.getvolume()[0] > 0:
                  #          self.mixer.volume = self.mixer.getvolume()
                  #          self.mixer.set_volume(0)
                  #          self.lcd.write_words("Mute", self.lcd.get_buffer()[1])
                  #      else:
                  #          self.mixer.set_volume(self.mixer.volume)
                  #          self.lcd.write_words("Unmute", self.lcd.get_buffer()[1])
                    else:
                        _LOGGER.warning("Unsupported key: %s", key_event.keycode)
                except TypeError as e:
                    _LOGGER.error("Error processing key: %s", str(key_event.keycode))
                    _LOGGER.error(e)

    def process_numbers(self, word: str) -> str:
        # if no digit found, return
        if not any(char.isdigit() for char in word):
            return word
        words = split_alpha_num(word)
        for i, word in enumerate(words):
            if word.isdigit():
                words[i] = num2words(word, lang="fr_CH")
                words[i] = words[i].replace("huitante", "quatre-vingt").replace("vingt et un", "vingt-et-un")
        return "".join(words)

    def process_letter(self, _letter: str, print=True) -> None:
        if _letter in {"\n", " ", "\r"}:
            if self.word == "exitnowarn":
                logging.warn("Exit the script")
                self.lcd.clear()
                sys.exit(0)
            if self.word:
                self.word = self.process_numbers(self.word)
                _LOGGER.info("playing word: %s", self.word)
                self.streamer.play(self.word)
                if print:
                    self.lcd.write_words(self.word.upper(), "")
                self.word = ""
            return
        _letter = _letter.lower()
        if not _letter.isalnum():
            return
        _LOGGER.debug("Got letter: %s", _letter)

        self.word += _letter
        self.lcd.add_letter(_letter.upper())
        self.streamer.play(f" {_letter} ")

    def loop(self):
        _LOGGER.debug("Starting main loop")
        _letter = self.get_one_letter()
        while True:
            try:
                self.process_letter(_letter)
                _letter = self.get_one_letter()
            except Exception as e:
                _LOGGER.error("Critical Exception: %s", e)
