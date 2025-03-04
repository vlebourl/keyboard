import logging
import os
import platform
import re
import secrets
import sys
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from audio import PygameMP3Player
from const import ALLOWED_CHARS, COMMON_LETTERS, DICTIONARY, MODES
from num2words import num2words

_LOGGER = logging.getLogger(__name__)

# Constants
KB_UTIL = (
    "evdev"
    if platform.system() == "Linux" and "DISPLAY" not in os.environ
    else "pynput"
)
MAGIC_KILL = "*-!this_is_a_safe_magic_string_to_kill_the_loop"

if KB_UTIL == "pynput":
    from keyboard_pynput import Keyboard
elif KB_UTIL == "evdev":
    from keyboard_evdev import Keyboard
else:
    raise ValueError(f"Unsupported KB_UTIL: {KB_UTIL}")


@dataclass
class GameScore:
    """Represents a score for a word in the guessing game."""

    correct: int = 0
    incorrect: int = 0


class Loop:
    """Main class handling the keyboard input loop and game modes."""

    def __init__(self) -> None:
        """Initialize the Loop with necessary components."""
        self.word: str = ""
        self.word_split_pattern = re.compile(r"[A-Za-z]+|\d+")
        self.keyboard = Keyboard()
        self.player = PygameMP3Player()
        self._mode: str = "0"
        self._score: Dict[str, GameScore] = {}

    def _process_numbers(self, word: str) -> str:
        """Convert numbers in text to their word representation.

        Args:
            word: Input string that may contain numbers

        Returns:
            String with numbers converted to words
        """
        if not any(char.isdigit() for char in word):
            return word

        words = self.word_split_pattern.findall(word)
        return " ".join(
            self._convert_number_to_words(part) if part.isdigit() else part
            for part in words
        )

    def _convert_number_to_words(self, number: str) -> str:
        """Convert a numeric string to its word representation in French.

        Args:
            number: String containing a number

        Returns:
            French word representation of the number
        """
        words = num2words(number, lang="fr_CH")
        return words.replace("huitante", "quatre-vingt").replace(
            "vingt et un", "vingt-et-un"
        )

    def _process_letter(self, letter: str) -> Optional[str]:
        """Process a single letter input and update game state.

        Args:
            letter: The input letter to process

        Returns:
            Optional string for special commands, empty string otherwise
        """
        if letter in {"\n", "\r"}:
            return self._process_word()
        if letter not in ALLOWED_CHARS:
            return ""

        _LOGGER.debug("Got letter: %s", letter)
        self.word += letter
        letter_sound = "espace" if letter == " " else letter
        self.player.open_mp3_string_and_play(f" {letter_sound} ")
        return ""

    def _process_word(self) -> str:
        """Process the completed word and handle special commands.

        Returns:
            String indicating action to take or empty string
        """
        self.word = self.word.strip()
        if not self.word:
            return ""

        if self.word == "exitnowarn":
            logging.warning("Exit the script")
            sys.exit(0)
        elif self.word == "printscore":
            self._print_scores()
            self.word = ""
            return ""
        elif self.word == "changemode":
            self.select_game_mode()
            self.word = ""
            return MAGIC_KILL

        return self._play_word()

    def _print_scores(self) -> None:
        """Print the current scores for all words."""
        for word, score in self._score.items():
            _LOGGER.info(
                f"{word}: {score.correct} correct, {score.incorrect} incorrect"
            )

    def _play_word(self) -> str:
        """Play the current word and reset the word buffer.

        Returns:
            The processed word that was played
        """
        self.word = self._process_numbers(self.word)
        _LOGGER.info("playing word: %s", self.word)
        self.player.open_mp3_string_and_play(self.word)
        word = self.word
        self.word = ""
        return word

    def preload(self) -> None:
        """Preload common letters and display welcome message."""
        _LOGGER.info("Preloading common letters")
        for letter in COMMON_LETTERS:
            if f" {letter} " not in self.player.generated_words:
                _LOGGER.info("    Preloading letter: %s", letter)
                self.player.preload_sound(f" {letter} ")

        self.player.save_common_words()
        _LOGGER.info("Preloaded words are:")
        for word in self.player.generated_words:
            _LOGGER.info("    %s", word)

        self.player.open_mp3_string_and_play(
            "Bonjour, bienvenue sur le clavier parlant."
        )

    def select_game_mode(self) -> None:
        """Handle game mode selection."""
        _LOGGER.info("Select game mode:")
        _LOGGER.info("  - mode 1: mode classique")
        _LOGGER.info("  - mode 2: écris le nombre")
        _LOGGER.info("  - mode 3: écris le mot")
        self.player.open_mp3_string_and_play(
            "Choisis un mode de jeu: un, écriture libre ; deux, écris le nombre ; trois, écris le mot"
        )

        selected_mode = ""
        while selected_mode not in ["1", "2", "3"]:
            selected_mode = self.keyboard.get_one_letter()
            _LOGGER.info(selected_mode)

        self.player.open_mp3_string_and_play(
            f"Tu as choisis le mode {MODES[selected_mode]}"
        )
        self._mode = selected_mode

    def generate_number_to_guess(self) -> str:
        """Generate a random word or number for the guessing game.

        Returns:
            String to be guessed by the player
        """
        size = 2 + secrets.randbelow(2)
        number = "".join([str(secrets.randbelow(10)) for _ in range(size)])
        to_guess = number.lstrip("0") or "0"
        return self._process_numbers(to_guess)

    def generate_word_to_guess(self) -> str:
        """Generate a random word or number for the guessing game.

        Returns:
            String to be guessed by the player
        """
        return DICTIONARY[secrets.randbelow(len(DICTIONARY))]

    def loop(self) -> None:
        """Main game loop that handles different game modes."""
        modes = {
            "1": self._run_classic_mode,
            "2": self._run_guessing_mode,
            "3": self._run_guessing_mode,
        }

        while True:
            if self._mode not in modes:
                self.select_game_mode()
            try:
                modes[self._mode](self._mode)
            except Exception as e:
                _LOGGER.error("Critical Exception: %s", e)

    def _run_classic_mode(self, mode: str) -> None:
        """Run the classic mode game loop."""
        _LOGGER.info(f"Running classic mode {mode}")
        while True:
            letter = self.keyboard.get_one_letter()
            word = self._process_letter(letter)
            if word == MAGIC_KILL:
                break

    def _run_guessing_mode(self, mode: str) -> None:
        """Run the guessing mode game loop."""
        _LOGGER.info(f"Running guessing mode {mode}")
        if mode == "2":
            generate = self.generate_number_to_guess
        elif mode == "3":
            generate = self.generate_word_to_guess
        target_word = generate()
        self.player.open_mp3_string_and_play(f"Ecris : {target_word}")
        _LOGGER.info(f"Ecris: {target_word}")

        while True:
            letter = self.keyboard.get_one_letter()
            word = self._process_letter(letter)
            if letter in {"\n", "\r"}:
                if word == MAGIC_KILL:
                    break

                guess = word.lstrip("0") or "0"
                if target_word not in self._score:
                    self._score[target_word] = GameScore()

                if guess.strip() == target_word:
                    self.player.open_mp3_string_and_play("Bravo")
                    self._score[target_word].correct += 1
                    target_word = generate()
                    self.player.open_mp3_string_and_play(f"Ecris : {target_word}")
                    _LOGGER.info(f"Ecris: {target_word}")
                else:
                    _LOGGER.info(f"Guessed: {guess}")
                    self.player.open_mp3_string_and_play(
                        f"Pas tout à fait... Ecris {target_word}"
                    )
                    self._score[target_word].incorrect += 1
