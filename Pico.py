"""A class to generate a wave file from text using Pico TTS.
"""

from picotts import PicoTTS


class TTS:
    """Generate a wave file from text using Pico TTS."""

    def __init__(self, language: str = "fr-FR"):
        """Initialize the Pico TTS engine.

        Args:
            language (str, optional): Language to speak in. Defaults to "en-US".
        """
        self.picotts = PicoTTS()
        self.picotts.voice(language)

    def generate(self, text: str) -> str:
        """Generate a wave file from text using Pico TTS.

        Args:
            text (str): The text to generate a wave file from.

        Returns:
            str: The wave file as a string.
        """
        return self.picotts.synth_wav(text)
