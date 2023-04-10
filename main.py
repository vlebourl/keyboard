"""
main file
"""

import time
from KeyboardPlayer import Keyboard
from util import internet_on

if __name__ == '__main__':
    while not internet_on():
        time.sleep(1)
    internet = True
    keyboard = Keyboard(internet)
    keyboard.word = "Bonjour, bienvenue sur le clavier parlant."
    if internet:
        keyboard.word += "internet actif."
    keyboard.process_letter("\n")
    keyboard.loop()
