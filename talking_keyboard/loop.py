import logging
import os
import platform
import re
import sys

from audio import PygameMP3Player
from const import COMMON_LETTERS, ALLOWED_CHARS
from num2words import num2words

_LOGGER = logging.getLogger(__name__)


KB_UTIL = (
    "evdev"
    if platform.system() == "Linux" and "DISPLAY" not in os.environ
    else "pynput"
)

if KB_UTIL == "pynput":
    from keyboard_pynput import Keyboard
elif KB_UTIL == "evdev":
    from keyboard_evdev import Keyboard
else:
    raise ValueError(f"Unsupported KB_UTIL: {KB_UTIL}")


class Loop:
    word = ""

    def __init__(self):
        self.word_split_pattern = re.compile(r"[A-Za-z]+|\d+")
        self.keyboard = Keyboard()
        self.player = PygameMP3Player()

    def _process_numbers(self, word: str) -> str:
        # Check for digits and return early if none are found
        for char in word:
            if char.isdigit():
                break
        else:
            return word

        # Split the word into alphanumeric and numeric parts
        words = self.word_split_pattern.findall(word)

        for i, part in enumerate(words):
            if part.isdigit():
                words[i] = self._convert_number_to_words(part)

        return " ".join(words)

    def _convert_number_to_words(self, number: str) -> str:
        # Convert the number to words (assuming num2words is a function that does this)
        words = num2words(number, lang="fr_CH")
        words = words.replace("huitante", "quatre-vingt").replace(
            "vingt et un", "vingt-et-un"
        )
        return words

    def _process_letter(self, _letter: str) -> None:
        if _letter in {"\n", "\r"}:
            self._process_word()
            return
        if _letter not in ALLOWED_CHARS:
            return
        _LOGGER.debug("Got letter: %s", _letter)
        self.word += _letter
        _letter = "espace" if _letter == " " else _letter
        self.player.open_mp3_string_and_play(f" {_letter} ")

    def _process_word(self):
        if self.word == "exitnowarn":
            logging.warning("Exit the script")
            sys.exit(0)
        if self.word:
            self.word = self._process_numbers(self.word)
            _LOGGER.info("playing word: %s", self.word)
            self.player.open_mp3_string_and_play(self.word)
            self.word = ""

    def preload(self):
        _LOGGER.info("Preloading common letters")
        for letter in COMMON_LETTERS:
            if f" {letter} " not in self.player.generated_words:
                _LOGGER.info("    Preloading letter: %s", letter)
                self.player.preload_sound(f" {letter} ")
        self.player.save_common_words()
        _LOGGER.info("Preloaded words are:")
        for word in self.player.generated_words.keys():
            _LOGGER.info("    %s", word)
        self.word = "Bonjour, bienvenue sur le clavier parlant."
        self._process_letter("\n")

    def loop(self):
        _LOGGER.debug("Starting main loop")
        _letter = self.keyboard.get_one_letter()
        while True:
            try:
                self._process_letter(_letter)
                _letter = self.keyboard.get_one_letter()
            except Exception as e:
                _LOGGER.error("Critical Exception: %s", e)
