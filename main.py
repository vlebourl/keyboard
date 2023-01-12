"""
main file
"""

from KeyboardPlayer import Keyboard
from util import internet_on

if __name__ == '__main__':
    internet = internet_on()
    keyboard = Keyboard(internet)
    keyboard.word = "Bonjour, bienvenu sur le clavier parlant."
    keyboard.process_letter("\n")
    keyboard.loop()