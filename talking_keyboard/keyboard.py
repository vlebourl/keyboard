import glob
import logging

from const import KEY_MAP
from evdev import InputDevice, categorize, ecodes

_LOGGER = logging.getLogger(__name__)


class Keyboard:
    def __init__(self, path=None):
        if path is None:
            _device_paths = glob.glob("/dev/input/by-id/*kbd*")
            if not _device_paths:
                _device_paths = glob.glob("/dev/input/by-id/*ogitech*")
                # _device_paths = glob.glob("/dev/input/by-id/*keyboard*")
            if not _device_paths:
                raise ValueError("No keyboard device found!")
            path = _device_paths[min(1, len(_device_paths))]

        self.device = InputDevice(path)
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

    def get_one_letter(self) -> str:
        for event in self.device.read_loop():
            if event.type != ecodes.EV_KEY:
                continue
            key_event = categorize(event)
            self.update_key_states(key_event)
            if key_event.keystate == key_event.key_up:
                try:
                    if mapped_key := KEY_MAP.get(
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
