import argparse
import logging
import threading
import time

from const import COMMON_LETTERS, KEY_MAP
from keyboard import Keyboard
from led import LEDStrip


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Talking keyboard with adjustable logging level"
    )
    parser.add_argument(
        "--loglevel",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: %(default))",
    )
    return parser.parse_args()


args = parse_arguments()
numeric_level = getattr(logging, args.loglevel.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError(f"Invalid log level: {args.loglevel}")

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.info("Starting up with log level %d", numeric_level)

if __name__ == "__main__":
    with LEDStrip() as led_strip:
        led_strip.flash(led_strip.WHITE, do_stop=False)
        _LOGGER.info("Starting talking keyboard")
        green_thread = threading.Thread(
            target=led_strip.running_leds,
            args=(led_strip.GREEN, 0.1, led_strip.stop_green_thread),
            daemon=True,
        )
        green_thread.start()
        time.sleep(2)

        keyboard = Keyboard(led_strip=led_strip)

        _LOGGER.info("Preloading common letters")
        for letter in COMMON_LETTERS:
            if f" {letter} " not in keyboard.player.generated_words:
                _LOGGER.info("    Preloading letter: %s", letter)
                keyboard.player.preload_sound(f" {letter} ")
        keyboard.player.save_common_words()

        _LOGGER.info("Preloaded words are:")
        for word in keyboard.player.generated_words.keys():
            _LOGGER.info("    %s", word)

        keyboard.word = "Bonjour, bienvenue sur le clavier parlant."
        keyboard.process_letter("\n", False)

        save_thread = threading.Thread(
            target=keyboard.player.periodic_save, args=(300,), daemon=True
        )
        save_thread.start()

        led_strip.light_up(led_strip.OFF)
        for v in led_strip.generate_color_map(KEY_MAP).values():
            led_strip.light_up(v)
            time.sleep(0.05)
        led_strip.flash(led_strip.GREEN)
        led_strip.light_up(led_strip.OFF)

        keyboard.lcd.lcd.clear()
        keyboard.lcd.buffer = ["BONJOUR LENAIC", "ECRIS UNE LETTRE"]
        keyboard.lcd._write_buffer()

        keyboard.loop()
