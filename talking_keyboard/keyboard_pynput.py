import logging

from const import DIGITS_MAP, KEY_MAP
from pynput import keyboard

_LOGGER = logging.getLogger(__name__)


class Keyboard:
    def __init__(self):
        _LOGGER.debug("Loading with pynput")
        self.shift_pressed = False
        self.caps_lock = False
        self.current_letter = None

        # Listener for keyboard events
        self.listener = keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release
        )
        self.listener.start()

    def on_press(self, key):
        try:
            if key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self.shift_pressed = True
            elif key == keyboard.Key.caps_lock:
                self.caps_lock = not self.caps_lock
        except Exception as e:
            _LOGGER.error(f"Error processing key press: {e}")

    def on_release(self, key):
        try:
            # Check if a key maps to a character
            if hasattr(key, "char") and key.char is not None:
                char = key.char
                if char in DIGITS_MAP:
                    char = DIGITS_MAP[char]
                if self.caps_lock ^ self.shift_pressed:
                    char = char.upper() if char.islower() else char.lower()
                self.current_letter = char
            elif hasattr(key, "name") and key.name in KEY_MAP:
                self.current_letter = KEY_MAP[key.name]
            else:
                _LOGGER.warning("Unsupported key: %s", key)

            if key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                self.shift_pressed = False
        except Exception as e:
            _LOGGER.error(f"Error processing key release: {e}")

    def get_one_letter(self) -> str:
        self.current_letter = None
        while self.current_letter is None:
            pass
        return self.current_letter
