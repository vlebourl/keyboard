import logging
import secrets
import sys
from enum import Enum
from typing import Optional

from audio import PygameMP3Player
from const import COMMON_LETTERS, MODES
from dictionary_manager import DictionaryManager
from game_modes import ClassicModeHandler, GuessingModeHandler
from keyboard import get_keyboard
from score_manager import ScoreManager
from word_processor import WordProcessor

_LOGGER = logging.getLogger(__name__)

# Commandes spéciales pour l'interaction
EXIT_NOWARN = "exitnowarn"
PRINT_SCORE = "printscore"
CHANGE_MODE = "changemode"
ADD_WORD = "addword"


class GameMode(Enum):
    CLASSIC = "1"
    GUESS_NUMBER = "2"
    GUESS_WORD = "3"


class LoopExitException(Exception):
    """Exception personnalisée pour signaler la sortie de la boucle de jeu."""

    pass


class GameManager:
    """
    Classe principale gérant le jeu, les modes et les interactions utilisateur.
    """

    def __init__(self, dictionary_path: str, dictionary: list) -> None:
        """Initialise les composants essentiels du jeu."""
        self.keyboard = get_keyboard()
        self.player = PygameMP3Player()
        self.current_mode: Optional[GameMode] = None
        self.word_processor = WordProcessor()
        self.score_manager = ScoreManager()
        self.dictionary_manager = DictionaryManager(dictionary_path, dictionary)
        self.current_word = ""

    def preload_resources(self) -> None:
        """
        Précharge les sons associés aux lettres communes 
        et affiche le message de bienvenue.
        """
        _LOGGER.info("Préchargement des lettres communes")
        for letter in COMMON_LETTERS:
            if f" {letter} " not in self.player.generated_words:
                _LOGGER.info("    Préchargement de la lettre : %s", letter)
                self.player.preload_sound(f" {letter} ")

        if "internet non disponible" not in self.player.generated_words:
            self.player.preload_sound("internet non disponible")

        self.player.save_common_words()
        _LOGGER.info("Mots préchargés :")
        for word in self.player.generated_words:
            _LOGGER.info("    %s", word)

        self.player.open_mp3_string_and_play(
            "Bonjour, bienvenue sur le clavier parlant."
        )

    def choose_game_mode(self) -> None:
        """
        Invite l'utilisateur à sélectionner un mode de jeu 
        et met à jour le mode courant.
        """
        _LOGGER.info("Sélection du mode de jeu :")
        _LOGGER.info("  - Mode 1 : Mode classique")
        _LOGGER.info("  - Mode 2 : Écris le nombre")
        _LOGGER.info("  - Mode 3 : Écris le mot")
        self.player.open_mp3_string_and_play(
            """Choisis un mode de jeu : un, écriture libre ; 
            deux, écris le nombre ; trois, écris le mot"""
        )

        selected_mode = ""
        while selected_mode not in [mode.value for mode in GameMode]:
            selected_mode = self.keyboard.get_one_letter()
            _LOGGER.info("Mode sélectionné : %s", selected_mode)

        self.player.open_mp3_string_and_play(
            f"Tu as choisi le mode {MODES[selected_mode]}"
        )
        self.current_mode = GameMode(selected_mode)

    def generate_number_guess(self) -> str:
        """
        Génère un nombre aléatoire pour le mode devinette, le convertit en mots,
        et retourne le résultat.

        Returns:
            Une chaîne représentant le nombre en mots.
        """
        size = 2 + secrets.randbelow(2)
        number = "".join([str(secrets.randbelow(10)) for _ in range(size)])
        to_guess = number.lstrip("0") or "0"
        return self.word_processor.convert_numbers_in_text(to_guess)

    def handle_special_commands(self, command: str) -> bool:
        """
        Traite les commandes spéciales.

        Args:
            command: La commande à traiter

        Returns:
            True si une commande a été traitée, False sinon
        """
        if command == EXIT_NOWARN:
            _LOGGER.warning("Fermeture du script.")
            sys.exit(0)
        elif command == PRINT_SCORE:
            self.score_manager.display_scores()
            self.current_word = ""
            return True
        elif command == CHANGE_MODE:
            self.choose_game_mode()
            self.current_word = ""
            raise LoopExitException()
        elif command == ADD_WORD:
            self.add_word_to_dictionary()
            self.current_word = ""
            return True
        return False

    def add_word_to_dictionary(self) -> None:
        """
        Permet à l'utilisateur d'ajouter un nouveau mot au dictionnaire.
        """
        self.player.open_mp3_string_and_play("Ajoute un mot au dictionnaire")
        new_word = ""
        letter = self.keyboard.get_one_letter()
        while letter not in {"\n", "\r"}:
            new_word += letter
            letter = self.keyboard.get_one_letter()

        self.dictionary_manager.add_word(new_word, self.player)

    def run_game_loop(self) -> None:
        """
        Lance la boucle principale du jeu en fonction du mode sélectionné.
        """
        while True:
            if not self.current_mode:
                self.choose_game_mode()

            try:
                if self.current_mode == GameMode.CLASSIC:
                    handler = ClassicModeHandler(
                        self.player,
                        self.keyboard,
                        self.word_processor,
                        self.score_manager,
                    )
                elif self.current_mode == GameMode.GUESS_NUMBER:
                    handler = GuessingModeHandler(
                        self.player,
                        self.keyboard,
                        self.word_processor,
                        self.score_manager,
                        self.generate_number_guess,
                    )
                elif self.current_mode == GameMode.GUESS_WORD:
                    handler = GuessingModeHandler(
                        self.player,
                        self.keyboard,
                        self.word_processor,
                        self.score_manager,
                        self.dictionary_manager.generate_random_word,
                    )
                else:
                    self.choose_game_mode()
                    continue

                handler.run()
            except LoopExitException:
                continue
            except Exception as e:
                _LOGGER.error("Exception critique : %s", e)
