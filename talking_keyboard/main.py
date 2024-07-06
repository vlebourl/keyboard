import argparse
import logging

from keyboard import Keyboard
from lcd import LCDDisplay


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
        _LOGGER.info("Starting talking keyboard")
        # Initialize LCD
        lcd = LCDDisplay()
            
        lcd.write_words("wifi OK", "")
        keyboard = Keyboard(lcd=lcd)

        keyboard.word = "Bonjour, bienvenue sur le clavier parlant."
        keyboard.process_letter("\n", False)

        keyboard.lcd.lcd.clear()
        keyboard.lcd.buffer = ["BONJOUR LENAIC", "ECRIS UNE LETTRE"]
        keyboard.lcd._write_buffer()

        keyboard.loop()
