import logging
import re
import sys

from audio import PygameMP3Player
from const import COMMON_LETTERS
from num2words import num2words

from keyboard import Keyboard

_LOGGER = logging.getLogger(__name__)


class Loop:
    word = ""

    def __init__(self):
        self.keyboard = Keyboard()
        self.player = PygameMP3Player()

    def process_numbers(self, word: str) -> str:
        # if no digit found, return
        if not any(char.isdigit() for char in word):
            return word
        words = re.findall(r"[A-Za-z]+|\d+", word)
        for i, word in enumerate(words):
            if word.isdigit():
                words[i] = num2words(word, lang="fr_CH")
                words[i] = (
                    words[i]
                    .replace("huitante", "quatre-vingt")
                    .replace("vingt et un", "vingt-et-un")
                )
        return " ".join(words)

    def process_letter(self, _letter: str) -> None:
        if _letter in {"\n", "\r"}:
            self.process_word()
            return
        if not _letter.isalnum() and _letter != " ":
            return
        _LOGGER.debug("Got letter: %s", _letter)
        self.word += _letter
        _letter = "espace" if _letter == " " else _letter
        self.player.open_mp3_string_and_play(f" {_letter} ")

    def process_word(self):
        if self.word == "exitnowarn":
            logging.warning("Exit the script")
            sys.exit(0)
        if self.word:
            self.word = self.process_numbers(self.word)
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
        self.process_letter("\n")

    def loop(self):
        _LOGGER.debug("Starting main loop")
        _letter = self.keyboard.get_one_letter()
        while True:
            try:
                self.process_letter(_letter)
                _letter = self.keyboard.get_one_letter()
            except Exception as e:
                _LOGGER.error("Critical Exception: %s", e)
