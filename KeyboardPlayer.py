"""Keyboard PLayer Class
"""
import os

# from getch import getch

from Pico import TTS

# Import classes from other files
from WavePlayer import WavePlayer


import sys, tty, termios
def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

class Keyboard:
    """Keyboard Class
    This class is used to play each key stroke as a wave file.
    When a key is pressed, the key is converted to a wave file
    and played.
    When Enter is pressed, the word is converted to a wave file
    and played then the word is cleared
    """

    def __init__(self, internet: bool = False):
        self.player = WavePlayer(internet)
        self.tts = TTS(internet)
        self.word = ""
        self.letters = []

    def get_one_letter(self) -> str:
        """Get one letter from the keyboard.

        Returns:
            str: The letter that was pressed.
        """
        try:
            return getch()
        except OverflowError:
            return self.get_one_letter()

    def process_letter(self, letter: str) -> None:
        """Process a letter from the keyboard.
        If it is a letter, add it to the word.
        If it is Enter, say the word and clear it.

        Args:
            letter (str): The letter to process.
        """
        # if Ctrl-C or Ctrl-D, power off
        # if letter in {"\x03", "\x04"}:
        #     self.word = "Au revoir"
        #     self.process_letter("\n")
        #     os.system("systemctl poweroff")

        # if letter is "\n" or "space"
        if letter in {"\n", " ", "\r"}:
            # say the word
            if self.word == "":
                return
            self.player.open_wave_string(self.tts.generate(self.word))
            self.player.play()
            self.word = ""
            return
        if not letter.isalnum():
            return
        self.word += letter
        self.player.open_wave_string(self.tts.generate(f" {letter} "))
        self.player.play()

    def loop(self):
        """Loop forever, getting a letter and processing it."""
        letter = self.get_one_letter()
        while True:
            self.process_letter(letter)
            letter = self.get_one_letter()
