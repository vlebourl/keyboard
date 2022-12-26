"""
Enter a short sequence of keys on the keyboard then say it out loud
"""
import time

import pyttsx3
from getch import getch


class Session:
    def __init__(self) -> None:
        self.engine = pyttsx3.init()
        self.engine.setProperty("voice", "french")
        self.engine.setProperty("rate", 150)

    def get_one_letter(self) -> str:
        try:
            return getch()
        except OverflowError:
            return self.get_one_letter()

    def process_letter(self, letter: str) -> None:
        if not letter.isalpha():
            return
        self.say_word(letter)
        print(f"You typed: {letter}")

    def say_word(self, word: str) -> None:
        self.engine.say(word)
        self.engine.runAndWait()

    def start(self) -> None:
        self.say_word("Bonjour")
        letter = self.get_one_letter()
        try:
            while True:
                self.process_letter(letter)
                letter = self.get_one_letter()
        except KeyboardInterrupt:
            self.say_word("Au revoir")

    def run(self) -> None:
        self.start()


session = Session()
session.run()
