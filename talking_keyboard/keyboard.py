import logging
import os
import platform

from const import DIGITS_MAP, KEY_MAP

KB_UTIL = (
    "evdev"
    if platform.system() == "Linux" and "DISPLAY" not in os.environ
    else "pynput"
)

_LOGGER = logging.getLogger(__name__)

if KB_UTIL == "pynput":

    from const import DIGITS_MAP, KEY_MAP
    from pynput import keyboard

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
                    # Adjust character based on shift and caps lock states
                    char = key.char
                    if char in DIGITS_MAP:
                        char = DIGITS_MAP[char]
                    if self.caps_lock ^ self.shift_pressed:  # XOR for toggling case
                        char = char.upper() if char.islower() else char.lower()
                    self.current_letter = char
                elif hasattr(key, "name") and key.name in KEY_MAP:
                    # Handle special keys
                    self.current_letter = KEY_MAP[key.name]
                else:
                    _LOGGER.warning("Unsupported key: %s", key)

                if key == keyboard.Key.shift or key == keyboard.Key.shift_r:
                    self.shift_pressed = False
            except Exception as e:
                _LOGGER.error(f"Error processing key release: {e}")

        def get_one_letter(self) -> str:
            """Blocking call to return the next typed letter."""
            self.current_letter = None
            while self.current_letter is None:
                pass  # Wait for a key to be released and processed
            return self.current_letter

elif KB_UTIL == "evdev":

    import glob

    from const import EV_MAP
    from evdev import InputDevice, categorize, ecodes

    class Keyboard:

        def __init__(self):
            _LOGGER.debug("Loading with evdev")
            _device_paths = (
                glob.glob("/dev/input/by-id/*kbd*")
                or glob.glob("/dev/input/by-id/*ogitech*")
                or glob.glob("/dev/input/by-id/*keyboard*")
            )
            if not _device_paths:
                raise ValueError("No keyboard device found!")
            self.device = InputDevice(_device_paths[1])
            self.shift_pressed = False
            self.caps_lock = False

        def update_key_states(self, key_event):
            if key_event.keycode in ["KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"]:
                self.shift_pressed = key_event.keystate == key_event.key_down
            elif (
                key_event.keycode == "KEY_CAPSLOCK"
                and key_event.keystate == key_event.key_down
            ):
                self.caps_lock = not self.caps_lock

        def get_one_letter(self):
            for event in self.device.read_loop():
                if event.type != ecodes.EV_KEY:
                    continue
                key_event = categorize(event)
                self.update_key_states(key_event)
                if key_event.keystate == key_event.key_up:
                    try:
                        if mapped_key := EV_MAP.get(
                            (
                                key_event.keycode[0]
                                if isinstance(key_event.keycode, list)
                                else key_event.keycode
                            ),
                            "",
                        ):
                            return mapped_key
                        else:
                            _LOGGER.warning("Unsupported key: %s", key_event.keycode)
                    except TypeError as e:
                        _LOGGER.error(
                            "Error processing key: %s", str(key_event.keycode)
                        )
                        _LOGGER.error(e)
