"""
A class to open a wav file and play it through pyAudio.
"""

import io
import wave

import pyaudio


class WavePlayer(object):
    """A class to open a wav file and play it through pyAudio."""

    def __init__(self):
        self.player = pyaudio.PyAudio()
        self.filename = None
        self.wave_file = None
        self.stream = None

    def open_wave_string(self, wave_string):
        """Open a wave file with io and prepare to play it.

        Args:
            wave_string (str): The wave file as a string.
        """
        self.filename = "wave_string"
        self.wave_file = wave.open(io.BytesIO(wave_string), "rb")
        self.stream = self.player.open(
            format=self.player.get_format_from_width(self.wave_file.getsampwidth()),
            channels=self.wave_file.getnchannels(),
            rate=self.wave_file.getframerate(),
            output=True,
        )

    def open_file(self, filename):
        """Open a wave file and prepare to play it.

        Args:
            filename (str): The full path to the wave file to play.
        """
        self.filename = filename
        self.wave_file = wave.open(filename, "rb")
        self.stream = self.player.open(
            format=self.player.get_format_from_width(self.wave_file.getsampwidth()),
            channels=self.wave_file.getnchannels(),
            rate=self.wave_file.getframerate(),
            output=True,
        )

    def play(self):
        """Play the wave file."""
        data = self.wave_file.readframes(32)
        while data != "":
            self.stream.write(data)
            data = self.wave_file.readframes(32)

    def close(self):
        """Close the wave file and terminate the pyAudio player."""
        self.stream.close()

    def __del__(self):
        self.player.terminate()
