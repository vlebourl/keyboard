import logging
from typing import Any, Callable, Optional

from const import ALLOWED_CHARS

_LOGGER = logging.getLogger(__name__)


class GameModeHandler:
    """Interface pour les gestionnaires de mode de jeu."""

    def __init__(
        self,
        game_manager: Any,
    ):
        self.game_manager = game_manager
        self.player = game_manager.player
        self.keyboard = game_manager.keyboard
        self.word_processor = game_manager.word_processor
        self.score_manager = game_manager.score_manager
        self.current_word = ""

    def handle_letter_input(self, letter: str) -> Optional[str]:
        """
        Gère la saisie d'une lettre et met à jour l'état du jeu.

        Args:
            letter: La lettre saisie par l'utilisateur.

        Returns:
            Une chaîne contenant une commande spéciale ou,
            dans le cas contraire, une chaîne vide.
        """
        if letter in {"\n", "\r"}:
            return self.finalize_word()
        if letter not in ALLOWED_CHARS:
            return ""

        _LOGGER.debug("Lettre reçue : %s", letter)
        self.current_word += letter
        letter_sound = "espace" if letter == " " else letter
        self.player.open_mp3_string_and_play(f" {letter_sound} ")
        return ""

    def finalize_word(self) -> str:
        """
        Finalise le mot en cours et le traite.

        Returns:
            Le mot traité.
        """
        self.current_word = self.word_processor.convert_numbers_in_text(
            self.current_word
        )

        from game_manager import LoopExitException

        try:
            if self.game_manager.handle_special_commands(self.current_word):
                return ""
        except LoopExitException:
            raise

        _LOGGER.info("Lecture du mot : %s", self.current_word)
        self.player.open_mp3_string_and_play(self.current_word)
        word_played = self.current_word
        self.current_word = ""
        return word_played

    def run(self) -> None:
        """Exécute la boucle de jeu pour ce mode."""
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")


class ClassicModeHandler(GameModeHandler):
    """Gestionnaire pour le mode classique."""

    def run(self) -> None:
        """Exécute la boucle de jeu pour le mode classique."""
        _LOGGER.info("Exécution du mode classique")
        while True:
            letter = self.keyboard.get_one_letter()
            self.handle_letter_input(letter)


class GuessingModeHandler(GameModeHandler):
    """Gestionnaire pour les modes de devinette."""

    def __init__(
        self,
        game_manager: Any,
        generate_target: Callable[[], str],
    ):
        super().__init__(game_manager)
        self.generate_target = generate_target
        self.target_word = ""

    def run(self) -> None:
        """Exécute la boucle de jeu pour le mode devinette."""
        _LOGGER.info("Exécution du mode devinette")
        self.target_word = self.generate_target()
        self.player.open_mp3_string_and_play(f"Ecris : {self.target_word}")
        _LOGGER.info(f"Ecris : {self.target_word}")

        while True:
            letter = self.keyboard.get_one_letter()
            word = self.handle_letter_input(letter)
            if letter in {"\n", "\r"}:
                guess = word.lstrip("0") or "0"

                if guess.strip() == self.target_word:
                    self.player.open_mp3_string_and_play("Bravo")
                    self.score_manager.update_score(True)
                    self.target_word = self.generate_target()
                    self.player.open_mp3_string_and_play(f"Ecris : {self.target_word}")
                    _LOGGER.info(f"Ecris : {self.target_word}")
                else:
                    _LOGGER.info(f"Devine : {guess}")
                    self.player.open_mp3_string_and_play(
                        f"""
                        Pas tout à fait... 
                        Ton score est de {self.score_manager.score}. 
                        Écris {self.target_word}
                        """
                    )
                    self.score_manager.reset_score()
