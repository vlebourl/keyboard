import logging
import os
import platform
import re
import secrets
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from audio import PygameMP3Player
from const import ALLOWED_CHARS, COMMON_LETTERS, MODES
from num2words import num2words

_LOGGER = logging.getLogger(__name__)

# ============================================================
# Configuration et Initialisation
# ============================================================

# Sélection de l'utilitaire de clavier en fonction du système
KB_UTIL = (
    "evdev"
    if platform.system() == "Linux" and "DISPLAY" not in os.environ
    else "pynput"
)

# Commandes spéciales pour l'interaction
EXIT_NOWARN = "exitnowarn"
PRINT_SCORE = "printscore"
CHANGE_MODE = "changemode"
ADD_WORD = "addword"

if KB_UTIL == "pynput":
    from keyboard_pynput import Keyboard
elif KB_UTIL == "evdev":
    from keyboard_evdev import Keyboard
else:
    raise ValueError(f"Unsupported KB_UTIL: {KB_UTIL}")

# Chargement du dictionnaire de mots
current_dir = os.path.dirname(os.path.abspath(__file__))
dictionary_path = os.path.join(current_dir, "dictionary.list")
with open(dictionary_path, encoding="utf-8") as f:
    DICTIONARY = [line.strip().lower() for line in f.readlines()]


# ============================================================
# Structures de Données et Énumérations
# ============================================================


@dataclass
class GameScore:
    """Représente le score associé à un mot dans le jeu de devinette."""

    correct: int = 0
    incorrect: int = 0


class GameMode(Enum):
    CLASSIC = "1"
    GUESS_NUMBER = "2"
    GUESS_WORD = "3"


class LoopExitException(Exception):
    """Exception personnalisée pour signaler la sortie de la boucle de jeu."""

    pass


# ============================================================
# Classe Principale: Loop
# ============================================================


class Loop:
    """
    Classe principale gérant la boucle d'entrée clavier et les différents modes de jeu.
    """

    def __init__(self) -> None:
        """Initialise les composants essentiels du jeu."""
        self.current_word: str = ""
        self.word_split_pattern = re.compile(r"[A-Za-z]+|\d+")
        self.keyboard = Keyboard()
        self.player = PygameMP3Player()
        self.current_mode: Optional[GameMode] = None
        self.scores: Dict[str, GameScore] = {}

    # ----------------------- Méthodes Publiques -----------------------

    def preload_resources(self) -> None:
        """
        Précharge les sons associés aux lettres communes et affiche le message de bienvenue.
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
        Invite l'utilisateur à sélectionner un mode de jeu et met à jour le mode courant.
        """
        _LOGGER.info("Sélection du mode de jeu :")
        _LOGGER.info("  - Mode 1 : Mode classique")
        _LOGGER.info("  - Mode 2 : Écris le nombre")
        _LOGGER.info("  - Mode 3 : Écris le mot")
        self.player.open_mp3_string_and_play(
            "Choisis un mode de jeu : un, écriture libre ; deux, écris le nombre ; trois, écris le mot"
        )

        selected_mode = ""
        while selected_mode not in [mode.value for mode in GameMode]:
            selected_mode = self.keyboard.get_one_letter()
            _LOGGER.info("Mode sélectionné : %s", selected_mode)

        self.player.open_mp3_string_and_play(
            f"Tu as choisi le mode {MODES[selected_mode]}"
        )
        self.current_mode = GameMode(selected_mode)

    def run_game_loop(self) -> None:
        """
        Lance la boucle principale du jeu en fonction du mode sélectionné.
        """
        modes = {
            GameMode.CLASSIC: self._run_classic_mode_loop,
            GameMode.GUESS_NUMBER: self._run_guessing_mode_loop,
            GameMode.GUESS_WORD: self._run_guessing_mode_loop,
        }

        while True:
            if self.current_mode not in modes:
                self.choose_game_mode()
            try:
                modes[self.current_mode](self.current_mode)
            except LoopExitException:
                break
            except Exception as e:
                _LOGGER.error("Exception critique : %s", e)

    def add_word_to_dictionary(self) -> None:
        """
        Permet à l'utilisateur d'ajouter un nouveau mot au dictionnaire.
        La vérification est insensible à la casse afin d'éviter les doublons.
        """
        self.player.open_mp3_string_and_play("Ajoute un mot au dictionnaire")
        new_word = ""
        letter = self.keyboard.get_one_letter()
        while letter not in {"\n", "\r"}:
            new_word += letter
            letter = self.keyboard.get_one_letter()  # Mise à jour continue de la saisie

        self.player.open_mp3_string_and_play(f"Tu veux ajouter le mot {new_word}")
        if not new_word.strip():
            self.player.open_mp3_string_and_play("Aucun mot n'a été saisi.")
            return

        # Comparaison insensible à la casse
        if new_word.strip().lower() in DICTIONARY:
            return
        DICTIONARY.append(new_word.strip().lower())
        with open(dictionary_path, "a+", encoding="utf-8") as f:
            f.write(f"{new_word.strip().lower()}\n")

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
        return self._convert_numbers_in_text(to_guess)

    def generate_dictionary_word(self) -> str:
        """
        Sélectionne aléatoirement un mot du dictionnaire pour le mode devinette.

        Returns:
            Le mot choisi.
        """
        return DICTIONARY[secrets.randbelow(len(DICTIONARY))]

    # ----------------------- Méthodes Privées -----------------------

    def _handle_letter_input(self, letter: str) -> Optional[str]:
        """
        Gère la saisie d'une lettre et met à jour l'état du jeu.

        Args:
            letter: La lettre saisie par l'utilisateur.

        Returns:
            Une chaîne contenant une commande spéciale ou, dans le cas contraire, une chaîne vide.
        """
        if letter in {"\n", "\r"}:
            return self._finalize_word()
        if letter not in ALLOWED_CHARS:
            return ""

        _LOGGER.debug("Lettre reçue : %s", letter)
        self.current_word += letter
        letter_sound = "espace" if letter == " " else letter
        self.player.open_mp3_string_and_play(f" {letter_sound} ")
        return ""

    def _finalize_word(self) -> str:
        """
        Finalise le mot en cours, vérifie la présence de commandes spéciales,
        et traite en conséquence.

        Returns:
            Le mot traité ou une commande.
        """
        final_word = self.current_word.strip()
        # Traitement insensible à la casse pour les commandes
        command = final_word.lower()
        if not final_word:
            return ""

        if command == EXIT_NOWARN:
            _LOGGER.warning("Fermeture du script.")
            sys.exit(0)
        elif command == PRINT_SCORE:
            self._display_scores()
            self.current_word = ""
            return ""
        elif command == CHANGE_MODE:
            self.choose_game_mode()
            self.current_word = ""
            raise LoopExitException()
        elif command == ADD_WORD:
            self.add_word_to_dictionary()
            self.current_word = ""
            return ""

        return self._finalize_and_play_word()

    def _finalize_and_play_word(self) -> str:
        """
        Convertit les nombres en mots, joue l'audio correspondant, et réinitialise le tampon de saisie.

        Returns:
            Le mot final traité et joué.
        """
        self.current_word = self._convert_numbers_in_text(self.current_word)
        _LOGGER.info("Lecture du mot : %s", self.current_word)
        self.player.open_mp3_string_and_play(self.current_word)
        word_played = self.current_word
        self.current_word = ""
        return word_played

    def _convert_numbers_in_text(self, text: str) -> str:
        """
        Convertit les nombres présents dans une chaîne en leur représentation verbale.

        Args:
            text: Chaîne susceptible de contenir des nombres.

        Returns:
            Chaîne avec les nombres convertis en mots.
        """
        if not any(char.isdigit() for char in text):
            return text

        words = self.word_split_pattern.findall(text)
        return " ".join(
            self._convert_number_to_words(part) if part.isdigit() else part
            for part in words
        )

    def _convert_number_to_words(self, number: str) -> str:
        """
        Convertit une chaîne numérique en sa représentation en mots en français.

        Args:
            number: Chaîne contenant un nombre.

        Returns:
            Représentation en mots du nombre.
        """
        words = num2words(number, lang="fr_CH")
        return words.replace("huitante", "quatre-vingt").replace(
            "vingt et un", "vingt-et-un"
        )

    def _display_scores(self) -> None:
        """
        Affiche les scores actuels pour chaque mot deviné.
        """
        for word, score in self.scores.items():
            _LOGGER.info(
                f"{word} : {score.correct} correct, {score.incorrect} incorrect"
            )

    def _run_classic_mode_loop(self, mode: GameMode) -> None:
        """
        Exécute la boucle de jeu pour le mode classique.

        Args:
            mode: Le mode de jeu en cours.
        """
        _LOGGER.info(f"Exécution du mode classique {mode.value}")
        while True:
            letter = self.keyboard.get_one_letter()
            self._handle_letter_input(letter)

    def _run_guessing_mode_loop(self, mode: GameMode) -> None:
        """
        Exécute la boucle de jeu pour le mode devinette.

        Args:
            mode: Le mode de jeu (GUESS_NUMBER ou GUESS_WORD).
        """
        _LOGGER.info(f"Exécution du mode devinette {mode.value}")
        if mode == GameMode.GUESS_NUMBER:
            generate = self.generate_number_guess
        elif mode == GameMode.GUESS_WORD:
            generate = self.generate_dictionary_word
        target_word = generate()
        self.player.open_mp3_string_and_play(f"Ecris : {target_word}")
        _LOGGER.info(f"Ecris : {target_word}")

        while True:
            letter = self.keyboard.get_one_letter()
            word = self._handle_letter_input(letter)
            if letter in {"\n", "\r"}:
                guess = word.lstrip("0") or "0"
                if target_word not in self.scores:
                    self.scores[target_word] = GameScore()

                if guess.strip() == target_word:
                    self.player.open_mp3_string_and_play("Bravo")
                    self.scores[target_word].correct += 1
                    target_word = generate()
                    self.player.open_mp3_string_and_play(f"Ecris : {target_word}")
                    _LOGGER.info(f"Ecris : {target_word}")
                else:
                    _LOGGER.info(f"Devine : {guess}")
                    self.player.open_mp3_string_and_play(
                        f"Pas tout à fait... Ecris {target_word}"
                    )
                    self.scores[target_word].incorrect += 1


# Fin du fichier complet
