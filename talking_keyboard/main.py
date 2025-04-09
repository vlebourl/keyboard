import argparse
import logging
import sys
import threading

import requests

from loop import Loop


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
    handlers=[logging.StreamHandler(sys.stdout)],
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.info("Starting up with log level %d", numeric_level)


def check_internet(url="https://www.google.com", timeout=5):
    try:
        response = requests.get(url, timeout=timeout)
        # Ensure the request was successful
        return response.status_code == 200
    except requests.ConnectionError:
        return False


def get_user_input(prompt):
    user_input = ""

    while True:
        char = input()
        if char == "\n":
            break
        elif char == "\b":
            user_input = user_input[:-1]
        elif char:
            user_input += char

    return user_input


if __name__ == "__main__":
    _LOGGER.info("Starting talking keyboard")

    loop = Loop()
    loop.preload_resources()

    wifi = check_internet()
    if not wifi:
        _LOGGER.error("No internet connection for TTS")
        loop.player.open_mp3_string_and_play("internet non disponible")
        exit

    loop.choose_game_mode()

    save_thread = threading.Thread(
        target=loop.player.periodic_save, args=(300,), daemon=True
    )
    save_thread.start()

    loop.run_game_loop()
