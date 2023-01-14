"""
A class to open a wav file and play it through pyAudio.
"""

import io
import time
import wave

import pyaudio
import pygame

class WavePlayer(object):
    """A class to open a wav file and play it through pyAudio."""

    def __init__(self, internet: bool = False):
        self._internet = internet
        if self._internet:
            pygame.init()
            self.player = pygame.mixer
            self.player.init()
        else:
            self.player = pyaudio.PyAudio()
            self.filename = None
            self.wave_file = None
            self.stream = None

    def open_wave_string(self, wave_string):
        """Open a wave file with io and prepare to play it.

        Args:
            wave_string (str): The wave file as a string.
        """
        if self._internet:
            self.player.music.load(wave_string, 'mp3')
        else:
            self.filename = "wave_string"
            self.wave_file = wave.open(io.BytesIO(wave_string), "rb")
            self.stream = self.player.open(
                format=self.player.get_format_from_width(self.wave_file.getsampwidth()),
                channels=self.wave_file.getnchannels(),
                rate=self.wave_file.getframerate(),
                output=True,
            )

    def play(self):
        """Play the wave file."""
        if self._internet:
            self.player.music.play()
            while self.player.music.get_busy():  # wait for music to finish playing
                time.sleep(0.01)
            return
        data = self.wave_file.readframes(1024)
        while data != "":
            self.stream.write(data)
            data = self.wave_file.readframes(1024)

    def close(self):
        """Close the wave file and terminate the pyAudio player."""
        self.stream.close()

    def __del__(self):
        if not self._internet:
            self.player.terminate()
