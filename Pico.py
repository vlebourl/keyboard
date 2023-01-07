"""A class to generate a wave file from text using Pico TTS.
"""

import subprocess
import tempfile

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

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        res = iter(process.stdout.readline, b"")
        return list(res) if sync else res

    # def say(self, txt, sync=False):
    #     txte = txt.encode('utf8')
    #     args = []
    #     args.append(txte)
    #     self._picotts_exe(args, sync=sync)

    def synth_wav(self, txt):

        wav = None

        with tempfile.NamedTemporaryFile(suffix=".wav") as f:

            txte = txt.encode("utf8")

            args = ["-w", f.name, txte]

            self._picotts_exe(args, sync=True)

            f.seek(0)
            wav = f.read()

        return wav

    @property
    def voices(self):
        return VOICES

    @property
    def voice(self):
        return self._voice

    def set_voice(self, v):
        if v in VOICES:
            self._voice = v
        else:
            print("Unknown voice, supported voices:{voices}".format(voices=VOICES))


class TTS:
    """Generate a wave file from text using Pico TTS."""

    def __init__(self, language: str = "fr-FR"):
        """Initialize the Pico TTS engine.

        Args:
            language (str, optional): Language to speak in. Defaults to "en-US".
        """
        self.picotts = PicoTTS()
        self.picotts.set_voice(language)

    def generate(self, text: str) -> str:
        """Generate a wave file from text using Pico TTS.

        Args:
            text (str): The text to generate a wave file from.

        Returns:
            str: The wave file as a string.
        """
        return self.picotts.synth_wav(text)
