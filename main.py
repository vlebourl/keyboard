"""
main file
"""

from KeyboardPlayer import Keyboard

if __name__ == '__main__':
    keyboard = Keyboard()
    keyboard.word = "Bonjour, bienvenu sur le clavier parlant."
    keyboard.process_letter("\n")
    keyboard.loop()