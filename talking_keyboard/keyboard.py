import glob
import logging
import sys

from evdev import InputDevice, categorize, ecodes

from talking_keyboard.audio import AlsaMixer, GoogleTTS, PygameMP3Player
from talking_keyboard.const import KEY_MAP

_LOGGER = logging.getLogger(__name__)

SWISS = {
    "70": "septante",
    "71": "septante et un",
    "72": "septante-deux",
    "73": "septante-trois",
    "74": "septante-quatre",
    "75": "septante-cinq",
    "76": "septante-six",
    "77": "septante-sept",
    "78": "septante-huit",
    "79": "septante-neuf",
    "90": "nonante",
    "91": "nonante et un",
    "92": "nonante-deux",
    "93": "nonante-trois",
    "94": "nonante-quatre",
    "95": "nonante-cinq",
    "96": "nonante-six",
    "97": "nonante-sept",
    "98": "nonante-huit",
    "99": "nonante-neuf"
}


class Keyboard:
    def __init__(self, led_strip, lcd):
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
        self.lcd = lcd

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
                        self.mixer.set_volume(min(self.mixer.getvolume() + 5, 100))
                        self.lcd.write_words(f"Volume up: {self.mixer.getvolume()}", self.lcd.get_buffer()[1])
                    elif key_event.keycode == "KEY_VOLUMEDOWN":
                        self.mixer.set_volume(min(self.mixer.getvolume() - 5, 100))
                        self.lcd.write_words(f"Volume down: {self.mixer.getvolume()}", self.lcd.get_buffer()[1])
                    elif (
                        isinstance(key_event.keycode, list)
                        and key_event.keycode[0] == "KEY_MIN_INTERESTING"
                    ):
                        if self.mixer.mixer.getvolume()[0] > 0:
                            self.mixer.volume = self.mixer.getvolume()
                            self.mixer.set_volume(0)
                            self.lcd.write_words("Mute", self.lcd.get_buffer()[1])
                        else:
                            self.mixer.set_volume(self.mixer.volume)
                            self.lcd.write_words("Unmute", self.lcd.get_buffer()[1])
                    else:
                        _LOGGER.warning("Unsupported key: %s", key_event.keycode)
                except TypeError as e:
                    self.led_strip.flash(self.led_strip.RED)
                    _LOGGER.error("Error processing key: %s", str(key_event.keycode))
                    _LOGGER.error(e)

    def process_swiss(self) -> None:
        try:
            word = int(self.word)
            if self.word in SWISS.keys():
                self.word = SWISS[self.word]
                _LOGGER.debug(f"found a Swiss number, converting to {self.word}")
                return
            if word > 99:
                preword = 100 * (int( word / 100))
                postword = str(word - preword)
                if postword in SWISS.keys():
                    self.word = f"{preword}-{SWISS[postword]}"
                    _LOGGER.debug(f"found a Swiss number, converting to {self.word}")
        except ValueError:
            return 

    def process_letter(self, _letter: str, print=True) -> None:
        if _letter in {"\n", " ", "\r"}:
            if self.word == "exitnowarn":
                logging.warn("Exit the script")
                sys.exit(0)
            self.process_swiss()
            if self.word in SWISS.keys():
                self.word = SWISS[self.word]
            if self.word:
                _LOGGER.info("playing word: %s", self.word)
                self.led_strip.light_up(self.led_strip.OFF)
                self.player.open_mp3_string_and_play(self.word)
                if print:
                    self.lcd.write_words(self.word.upper(), "")
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
