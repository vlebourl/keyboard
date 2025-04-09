import logging
from dataclasses import dataclass
from typing import Dict

_LOGGER = logging.getLogger(__name__)


@dataclass
class GameScore:
    """Représente le score associé à un mot dans le jeu de devinette."""

    correct: int = 0
    incorrect: int = 0


class ScoreManager:
    """Classe responsable de la gestion des scores."""

    def __init__(self):
        self.scores: Dict[str, GameScore] = {}

    def update_score(self, word: str, correct: bool) -> None:
        """
        Met à jour le score pour un mot donné.

        Args:
            word: Le mot à évaluer
            correct: Si la réponse était correcte
        """
        if word not in self.scores:
            self.scores[word] = GameScore()

        if correct:
            self.scores[word].correct += 1
        else:
            self.scores[word].incorrect += 1

    def display_scores(self) -> None:
        """
        Affiche les scores actuels pour chaque mot deviné.
        """
        for word, score in self.scores.items():
            _LOGGER.info(
                f"{word} : {score.correct} correct, {score.incorrect} incorrect"
            )
