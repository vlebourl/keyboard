import glob
import logging

from const import EV_MAP
from evdev import EvdevError, InputDevice, categorize, ecodes

_LOGGER = logging.getLogger(__name__)


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
        for device in _device_paths:
            try:
                candidate_device = InputDevice(device)
                self.device = candidate_device
                break
            except (OSError, EvdevError) as e:  # Replace with specific exceptions.
                _LOGGER.debug(f"Failed to initialize device {device}: {e}")
        else:
            raise RuntimeError("No valid input device found.")
        self.shift_pressed = False
        self.caps_lock = False

    def _update_key_states(self, key_event):
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
            self._update_key_states(key_event)
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
                    _LOGGER.error("Error processing key: %s", str(key_event.keycode))
                    _LOGGER.error(e)
