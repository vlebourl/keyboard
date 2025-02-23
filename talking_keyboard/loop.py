import logging
import os
import platform
import random
import re
import sys
import time

from num2words import num2words

from audio import PygameMP3Player
from const import ALLOWED_CHARS, COMMON_LETTERS, DICTIONARY, MODES

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
        self._mode = 0
        self._score = {}

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
            return self._process_word()
        if _letter not in ALLOWED_CHARS:
            return ""
        _LOGGER.debug("Got letter: %s", _letter)
        self.word += _letter
        _letter = "espace" if _letter == " " else _letter
        self.player.open_mp3_string_and_play(f" {_letter} ")
        return ""

    def _process_word(self):
        self.word = self.word.strip()
        if len(self.word) == 0:
            return ""
        if self.word == "exitnowarn":
            logging.warning("Exit the script")
            sys.exit(0)
        if self.word == "printscore":
            for key, value in self._score.items():
                _LOGGER.info(f"{key}: {value[0]} correct, {value[1]} incorrect")
            self.word = ""
            return ""
        if self.word == "changemode":
            self.select_game_mode()
            self.word = ""
            return "kill_loop"
        if self.word:
            self.word = self._process_numbers(self.word)
            _LOGGER.info("playing word: %s", self.word)
            self.player.open_mp3_string_and_play(self.word)
            word = self.word
            self.word = ""
            return word

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
        self.player.open_mp3_string_and_play(
            "Bonjour, bienvenue sur le clavier parlant."
        )

    def select_game_mode(self):
        _LOGGER.info("Select game mode:")
        _LOGGER.info("  - mode 1: mode classique")
        _LOGGER.info("  - mode 2: écris la proposition")
        self.player.open_mp3_string_and_play("Choisis un mode de jeu: 1 ou 2")
        _letter = 0
        while _letter not in ["1", "2"]:
            _letter = self.keyboard.get_one_letter()
        self.player.open_mp3_string_and_play(f"Tu as choisis le mode {MODES[_letter]}")
        self._mode = _letter

    def to_guess(self):
        choose = random.randint(0, 9)
        if choose > 5:
            size = random.randint(2, 4)
            to_guess = (
                "".join([str(random.randint(0, 9)) for _ in range(size)]).lstrip("0")
                or "0"
            )
            to_guess = self._process_numbers(to_guess)
        else:
            # Choose a random word from the dictionary
            to_guess = random.choice(DICTIONARY)
        self.player.open_mp3_string_and_play(f"Ecris : {to_guess}")
        _LOGGER.info(f"Ecris: {to_guess}")
        return to_guess

    def loop(self):
        _LOGGER.debug("Starting main loop")
        if self._mode == "1":
            _letter = self.keyboard.get_one_letter()
            while True:
                try:
                    word = self._process_letter(_letter)
                    if word == "kill_loop":
                        break
                    _letter = self.keyboard.get_one_letter()
                except Exception as e:
                    _LOGGER.error("Critical Exception: %s", e)
        elif self._mode == "2":
            to_guess = self.to_guess()
            _letter = self.keyboard.get_one_letter()
            while True:
                try:
                    word = self._process_letter(_letter)
                    if _letter in {"\n", "\r"}:
                        if word == "kill_loop":
                            break
                        result = word.lstrip("0") or "0"
                        if result.strip() == to_guess:
                            self.player.open_mp3_string_and_play("Bravo")
                            self._score[to_guess] = (
                                self._score.get(to_guess, (0, 0))[0] + 1,
                                self._score.get(to_guess, (0, 0))[1],
                            )
                            to_guess = self.to_guess()
                        else:
                            _LOGGER.info(f"Guessed: {result}")
                            self.player.open_mp3_string_and_play(
                                f"Pas tout à fait... Ecris {to_guess}"
                            )
                            self._score[to_guess] = (
                                self._score.get(to_guess, (0, 0))[0],
                                self._score.get(to_guess, (0, 0))[1] + 1,
                            )
                    _letter = self.keyboard.get_one_letter()
                except Exception as e:
                    _LOGGER.error("Critical Exception: %s", e)
        self.loop()
