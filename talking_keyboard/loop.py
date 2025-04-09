import logging
import os
from typing import Optional

from const import ALLOWED_CHARS
from game_manager import GameManager, GameMode, LoopExitException
from game_modes import ClassicModeHandler, GuessingModeHandler

_LOGGER = logging.getLogger(__name__)

# ============================================================
# Configuration et Initialisation
# ============================================================

# Chargement du dictionnaire de mots
current_dir = os.path.dirname(os.path.abspath(__file__))
dictionary_path = os.path.join(current_dir, "dictionary.list")
with open(dictionary_path, encoding="utf-8") as f:
    DICTIONARY = [line.strip().lower() for line in f.readlines()]


# ============================================================
# Classe de compatibilité pour maintenir l'API existante
# ============================================================


class Loop:
    """
    Classe principale gérant la boucle d'entrée clavier et les différents modes de jeu.
    Cette classe est maintenue pour la compatibilité avec le code existant.
    """

    def __init__(self) -> None:
        """Initialise le gestionnaire de jeu."""
        self.game_manager = GameManager(dictionary_path, DICTIONARY)

        # Pour la compatibilité avec le code existant
        self.current_word = ""
        self.word_split_pattern = self.game_manager.word_processor.word_split_pattern
        self.player = self.game_manager.player
        self.current_mode = None
        self.scores = self.game_manager.score_manager.scores

    def preload_resources(self) -> None:
        """Délègue au gestionnaire de jeu."""
        self.game_manager.preload_resources()

    def choose_game_mode(self) -> None:
        """Délègue au gestionnaire de jeu."""
        self.game_manager.choose_game_mode()
        self.current_mode = self.game_manager.current_mode

    def run_game_loop(self) -> None:
        """Délègue au gestionnaire de jeu."""
        self.game_manager.run_game_loop()

    def add_word_to_dictionary(self) -> None:
        """Délègue au gestionnaire de jeu."""
        self.game_manager.add_word_to_dictionary()

    def generate_number_guess(self) -> str:
        """Délègue au gestionnaire de jeu."""
        return self.game_manager.generate_number_guess()

    def generate_dictionary_word(self) -> str:
        """Délègue au gestionnaire de jeu."""
        return self.game_manager.dictionary_manager.generate_random_word()

    # Les méthodes privées sont maintenues pour la compatibilité
    def _handle_letter_input(self, letter: str) -> Optional[str]:
        """Méthode de compatibilité."""
        self.current_word = self.game_manager.current_word
        if letter in {"\n", "\r"}:
            result = self._finalize_word()
        elif letter not in ALLOWED_CHARS:
            result = ""
        else:
            _LOGGER.debug("Lettre reçue : %s", letter)
            self.current_word += letter
            letter_sound = "espace" if letter == " " else letter
            self.player.open_mp3_string_and_play(f" {letter_sound} ")
            result = ""
        self.game_manager.current_word = self.current_word
        return result

    def _finalize_word(self) -> str:
        """Méthode de compatibilité."""
        final_word = self.current_word.strip()
        command = final_word.lower()
        if not final_word:
            return ""

        try:
            if self.game_manager.handle_special_commands(command):
                return ""
        except LoopExitException:
            raise

        return self._finalize_and_play_word()

    def _finalize_and_play_word(self) -> str:
        """Méthode de compatibilité."""
        self.current_word = self.game_manager.word_processor.convert_numbers_in_text(
            self.current_word
        )
        _LOGGER.info("Lecture du mot : %s", self.current_word)
        self.player.open_mp3_string_and_play(self.current_word)
        word_played = self.current_word
        self.current_word = ""
        return word_played

    def _convert_numbers_in_text(self, text: str) -> str:
        """Méthode de compatibilité."""
        return self.game_manager.word_processor.convert_numbers_in_text(text)

    def _convert_number_to_words(self, number: str) -> str:
        """Méthode de compatibilité."""
        return self.game_manager.word_processor.convert_number_to_words(number)

    def _display_scores(self) -> None:
        """Méthode de compatibilité."""
        self.game_manager.score_manager.display_scores()

    def _run_classic_mode_loop(self, mode: GameMode) -> None:
        """Méthode de compatibilité."""
        handler = ClassicModeHandler(
            self.player,
            self.game_manager.keyboard,
            self.game_manager.word_processor,
            self.game_manager.score_manager,
        )
        handler.run()

    def _run_guessing_mode_loop(self, mode: GameMode) -> None:
        """Méthode de compatibilité."""
        if mode == GameMode.GUESS_NUMBER:
            generate = self.generate_number_guess
        elif mode == GameMode.GUESS_WORD:
            generate = self.generate_dictionary_word

        handler = GuessingModeHandler(
            self.player,
            self.game_manager.keyboard,
            self.game_manager.word_processor,
            self.game_manager.score_manager,
            generate,
        )
        handler.run()
