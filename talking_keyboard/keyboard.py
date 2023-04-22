import glob
import logging
import sys

from evdev import InputDevice, categorize, ecodes

from talking_keyboard.audio import AlsaMixer, GoogleTTS, PygameMP3Player
from talking_keyboard.const import KEY_MAP
from talking_keyboard.lcd import LCDDisplay

_LOGGER = logging.getLogger(__name__)


class Keyboard:
    def __init__(self, led_strip):
        self.led_strip = led_strip
        self.COLOR_MAP = self.led_strip.generate_color_map(KEY_MAP)
        _device_paths = glob.glob("/dev/input/by-id/*kbd*")
        if not _device_paths:
            _device_paths = glob.glob("/dev/input/by-id/*keyboard*")
        if not _device_paths:
            self.led_stripflash()
            raise ValueError("No keyboard device found!")
        self.device = InputDevice(_device_paths[0])
        self.mixer = AlsaMixer()

        self.mixer.set_volume(0 if logging.root.level == logging.DEBUG else 100)
        self.tts = GoogleTTS(led_strip)
        self.player = PygameMP3Player(self.tts)

        self.word = ""
        self.shift_pressed = False
        self.caps_lock = False
        self.lcd = LCDDisplay()

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
                    if mapped_key := KEY_MAP.get(
                        key_event.keycode[0]
                        if isinstance(key_event.keycode, list)
                        else key_event.keycode,
                        "",
                    ):
                        return mapped_key
                    elif key_event.keycode == "KEY_VOLUMEUP":
                        self.mixer.set_volume(min(self.mixer.mixer.getvolume()[0] + 5, 100))
                    elif key_event.keycode == "KEY_VOLUMEDOWN":
                        self.mixer.set_volume(min(self.mixer.mixer.getvolume()[0] - 5, 100))
                    elif (
                        isinstance(key_event.keycode, list)
                        and key_event.keycode[0] == "KEY_MIN_INTERESTING"
                    ):
                        if self.mixer.mixer.getvolume()[0] > 0:
                            self.mixer.volume = self.mixer.mixer.getvolume()[0]
                            self.mixer.set_volume(0)
                        else:
                            self.mixer.set_volume(self.mixer.volume)
                    else:
                        _LOGGER.warning("Unsupported key: %s", key_event.keycode)
                except TypeError:
                    self.led_strip.flash(self.led_strip.RED)
                    _LOGGER.error("Error processing key: %s", str(key_event.keycode))

    def process_letter(self, _letter: str, print=True) -> None:
        if _letter in {"\n", " ", "\r"}:
            if self.word == "exitnowarn":
                logging.warn("Exit the script")
                sys.exit(0)
            if self.word:
                _LOGGER.info("playing word: %s", self.word)
                self.led_strip.light_up(self.led_strip.OFF)
                self.player.open_mp3_string_and_play(self.word)
                if print:
                    self.lcd.write_word(self.word.upper())
                self.word = ""
            return
        _letter = _letter.lower()
        if not _letter.isalnum():
            return
        _LOGGER.debug("Got letter: %s", _letter)
        _LOGGER.debug("lighting up: %s", str(self.COLOR_MAP[_letter]))
        self.led_strip.light_up(self.COLOR_MAP[_letter])

        self.word += _letter
        self.lcd.add_letter(_letter.upper())
        self.player.open_mp3_string_and_play(f" {_letter} ")

    def loop(self):
        _LOGGER.debug("Starting main loop")
        _letter = self.get_one_letter()
        while True:
            try:
                self.process_letter(_letter)
                _letter = self.get_one_letter()
            except Exception as e:
                self.led_strip.flash(self.led_strip.RED)
                _LOGGER.error("Critical Exception: %s", e)
