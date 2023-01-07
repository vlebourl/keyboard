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

    def __del__(self):
        self.player.terminate()
    
    def _open_wave_string(self, wave_string):
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

    def _open_file(self, filename):
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

    def close(self):
        """Close the wave file and terminate the pyAudio player."""
        self.stream.close()

    def play(self, string, type="string"):
        """Play the wave file."""
        if type == "file":
            self._open_file(string)
        elif type == "string":
            self._open_wave_string(string)
        else:
            raise ValueError("Type must be 'file' or 'string'")
        data = self.wave_file.readframes(1024)
        while data != b'':
            self.stream.write(data)
            data = self.wave_file.readframes(1024)
        self.close()

