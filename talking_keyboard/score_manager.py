import logging

_LOGGER = logging.getLogger(__name__)


class ScoreManager:
    """Classe responsable de la gestion des scores."""

    def __init__(self):
        self.score: int = 0

    def update_score(self, correct: bool) -> None:
        """
        Met à jour le score pour un mot donné.

        Args:
            word: Le mot à évaluer
            correct: Si la réponse était correcte
        """

        if correct:
            self.score += 1

    def reset_score(self) -> None:
        """
        Réinitialise le score.
        """
        self.score = 0
        _LOGGER.info("Scores réinitialisés.")

    def display_scores(self) -> None:
        """
        Affiche le score actuel.
        """
        _LOGGER.info(f"Scores actuels : {self.score}")
