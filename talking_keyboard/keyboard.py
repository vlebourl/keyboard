import logging

from const import KB_UTIL

_LOGGER = logging.getLogger(__name__)

# Singleton instance
_keyboard_instance = None


class KeyboardWrapper:
    """
    Wrapper class that abstracts the complexity of different keyboard implementations.
    Implements the singleton pattern to ensure only one keyboard instance exists.
    """

    def __init__(self):
        """Initialize the appropriate keyboard implementation based on the system."""
        if KB_UTIL == "pynput":
            from keyboard_pynput import Keyboard

            _LOGGER.info("Using pynput keyboard implementation")
        elif KB_UTIL == "evdev":
            from keyboard_evdev import Keyboard

            _LOGGER.info("Using evdev keyboard implementation")
        else:
            raise ValueError(f"Unsupported KB_UTIL: {KB_UTIL}")

        self._keyboard = Keyboard()

    def get_one_letter(self):
        """
        Get one letter from the keyboard.

        Returns:
            str: The letter pressed by the user.
        """
        return self._keyboard.get_one_letter()


def get_keyboard():
    """
    Returns the singleton keyboard instance.
    Creates it if it doesn't exist yet.

    Returns:
        KeyboardWrapper: The single keyboard wrapper instance.
    """
    global _keyboard_instance

    if _keyboard_instance is None:
        _keyboard_instance = KeyboardWrapper()

    return _keyboard_instance
