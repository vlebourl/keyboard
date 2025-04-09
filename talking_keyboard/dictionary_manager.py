import secrets
from typing import List

from audio import PygameMP3Player


class DictionaryManager:
    """Classe responsable de la gestion du dictionnaire de mots."""

    def __init__(self, dictionary_path: str, dictionary: List[str]):
        self.dictionary_path = dictionary_path
        self.dictionary = dictionary

    def add_word(self, new_word: str, player: PygameMP3Player) -> None:
        """
        Ajoute un nouveau mot au dictionnaire.

        Args:
            new_word: Le mot à ajouter
            player: Le lecteur audio pour les retours vocaux
        """
        player.open_mp3_string_and_play(f"Tu veux ajouter le mot {new_word}")
        if not new_word.strip():
            player.open_mp3_string_and_play("Aucun mot n'a été saisi.")
            return

        # Comparaison insensible à la casse
        if new_word.strip().lower() in self.dictionary:
            return

        self.dictionary.append(new_word.strip().lower())
        with open(self.dictionary_path, "a+", encoding="utf-8") as f:
            f.write(f"{new_word.strip().lower()}\n")

    def generate_random_word(self) -> str:
        """
        Sélectionne aléatoirement un mot du dictionnaire.

        Returns:
            Le mot choisi.
        """
        return self.dictionary[secrets.randbelow(len(self.dictionary))]
