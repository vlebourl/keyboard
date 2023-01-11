"""A class to generate a wave file from text using Pico TTS.
"""

import io
import subprocess
import tempfile

from gtts import gTTS

from util import internet_on

VOICES = ["de-DE", "en-GB", "en-US", "es-ES", "fr-FR", "it-IT"]


class PicoTTS(object):
    """A wrapper for the Pico TTS engine.

    Args:
        voice (str): The voice to use. Defaults to "en-US".
    """

    def __init__(self, voice="en-US"):
        self._voice = voice

    def _picotts_exe(self, args, sync=False):
        cmd = [
            "pico2wave",
            "-l",
            self._voice,
        ]

        cmd.extend(args)

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        res = iter(process.stdout.readline, b"")
        return list(res) if sync else res

    # def say(self, txt, sync=False):
    #     txte = txt.encode('utf8')
    #     args = []
    #     args.append(txte)
    #     self._picotts_exe(args, sync=sync)

    def generate(self, txt):

        wav = None

        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            txte = txt.encode("utf8")
            args = ["-w", f.name, txte]
            self._picotts_exe(args, sync=True)
            f.seek(0)
            wav = f.read()

        return wav

    def set_voice(self, v):
        self._voice = v


class GoogleTTS:
    """Google Text to Speech"""

    def __init__(self, language: str = "fr"):
        """Initialize the Google TTS engine.

        Args:
            language (str, optional): Language to speak in. Defaults to "fr".
        """
        self._language = language[:2]

    def set_voice(self, language: str) -> None:
        """Set the language

        Args:
            language (str): the language
        """
        self._language = language[:2]

    def generate(self, text: str) -> str:
        """Generate a mp3 file from text

        Args:
            text (str): text to convert

        Returns:
            str: the wave in string format
        """
        tts = gTTS(text=text, lang=self._language)
        with io.BytesIO() as bytes_io:
            tts.write_to_fp(bytes_io)
            bytes_io.seek(0)
            return bytes_io.read()


class TTS:
    """Generate a wave file from text using Pico TTS."""

    def __init__(self, language: str = "fr-FR"):
        """Initialize the Pico TTS engine.

        Args:
            language (str, optional): Language to speak in. Defaults to "en-US".
        """
        self.tts = GoogleTTS() if internet_on() else PicoTTS()
        self.tts.set_voice(language)

    def generate(self, text: str) -> str:
        """Generate a wave file from text using Pico TTS.

        Args:
            text (str): The text to generate a wave file from.

        Returns:
            str: The wave file as a string.
        """
        return self.tts.generate(text)
