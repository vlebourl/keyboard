import argparse
import logging
import os
import subprocess
import sys
import threading
import time

from talking_keyboard.const import COMMON_LETTERS, KEY_MAP
from talking_keyboard.keyboard import Keyboard
from talking_keyboard.lcd import LCDDisplay
from talking_keyboard.led import LEDStrip


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

if os.geteuid() != 0:
    _LOGGER.error("This script must be run with sudo privileges.")
    sys.exit(1)

_LOGGER.info("Starting up with log level %d", numeric_level)

def check_internet_connection():
    try:
        response = subprocess.check_output("ping -c 1 google.com", shell=True)
        return True
    except subprocess.CalledProcessError:
        return False

def update_wpa_supplicant(ssid, psk):
    wpa_supplicant_path = "/etc/wpa_supplicant/wpa_supplicant.conf"

    with open(wpa_supplicant_path, "a") as f:
        f.write(f"\nnetwork={{\nssid=\"{ssid}\"\npsk=\"{psk}\"\n}}\n")

    subprocess.call(["sudo", "systemctl", "daemon-reload"])
    subprocess.call(["sudo", "systemctl", "restart", "dhcpcd"])

def get_user_input(prompt, lcd):
    lcd.write_words(prompt, "")
    user_input = ""

    while True:
        char = input()
        if char == '\n':
            break
        elif char == '\b':
            user_input = user_input[:-1]
            lcd.write_words(prompt, user_input)
        elif char:
            user_input += char
            lcd.add_letter(char)

    return user_input

if __name__ == "__main__":
    with LEDStrip() as led_strip:
        led_strip.flash(led_strip.WHITE)
        _LOGGER.info("Starting talking keyboard")
        green_thread = threading.Thread(
            target=led_strip.running_leds,
            args=(led_strip.GREEN, 0.1, led_strip.green_thread_event),
            daemon=True,
        )
        green_thread.start()
        time.sleep(2)
        # Initialize LCD
        lcd = LCDDisplay()

        wifi = check_internet_connection()
        # Check internet connection
        while not wifi:
            lcd.write_words("No wifi", "")
            time.sleep(2)
            ssid = get_user_input("wifi SSID:", lcd)
            psk = get_user_input("wifi PSK:", lcd)
            update_wpa_supplicant(ssid, psk)
            time.sleep(5)
            wifi = check_internet_connection()
            time.sleep(2)
            
        lcd.write_words("wifi OK", "")
        keyboard = Keyboard(led_strip=led_strip, lcd=lcd)

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
        led_strip.stop_green_thread(green_thread)
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
