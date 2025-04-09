import re

from num2words import num2words


class WordProcessor:
    """Classe responsable du traitement des mots et de la conversion des nombres."""

    def __init__(self):
        self.word_split_pattern = re.compile(r"[A-Za-z]+|\d+")

    def convert_numbers_in_text(self, text: str) -> str:
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
            self.convert_number_to_words(part) if part.isdigit() else part
            for part in words
        )

    def convert_number_to_words(self, number: str) -> str:
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
