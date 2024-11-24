import logging
import queue
import time

from const import DIGITS_MAP, KEY_MAP
from pynput import keyboard

_LOGGER = logging.getLogger(__name__)

shift_keys = {keyboard.Key.shift, keyboard.Key.shift_r}


class Keyboard:
    def __init__(self):
        _LOGGER.debug("Loading with pynput")
        self.shift_pressed = False
        self.caps_lock = False
        self.key_queue = queue.Queue()  # Queue to store key events

        # Listener for keyboard events
        self.listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release, suppress=False
        )
        self.listener.start()

    def _on_press(self, key):
        try:
            # Use a set for faster lookup
            if key in shift_keys:
                self.shift_pressed = True
            elif key == keyboard.Key.caps_lock:
                self.caps_lock = not self.caps_lock
        except Exception as e:
            _LOGGER.error(f"Error processing key press: {e}")

    def _on_release(self, key):
        try:
            if hasattr(key, "char") and key.char is not None:
                char = key.char
                if self.caps_lock ^ self.shift_pressed:
                    char = char.upper() if char.islower() else char.lower()
                self.key_queue.put(char)  # Add the key to the queue
            elif hasattr(key, "name") and key.name in KEY_MAP:
                self.key_queue.put(KEY_MAP[key.name])
            elif key in {keyboard.Key.shift, keyboard.Key.shift_r}:
                self.shift_pressed = False
        except Exception as e:
            _LOGGER.error(f"Error on key release: {e}")

    def get_one_letter(self):
        """Get the next key from the queue."""
        while True:
            try:
                return self.key_queue.get(timeout=0.1)  # Non-blocking wait
            except queue.Empty:
                continue
