import argparse
import logging
import os
import platform
import threading

import requests
from loop import Loop

KB_UTIL = (
    "evdev"
    if platform.system() == "Linux" and "DISPLAY" not in os.environ
    else "pynput"
)

if KB_UTIL == "pynput":
    from keyboard_pynput import Keyboard
elif KB_UTIL == "evdev":
    from keyboard_evdev import Keyboard
else:
    raise ValueError(f"Unsupported KB_UTIL: {KB_UTIL}")


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


def check_internet(url="https://www.google.com", timeout=5):
    try:
        response = requests.get(url, timeout=timeout)
        # Ensure the request was successful
        return response.status_code == 200
    except requests.ConnectionError:
        return False


# def update_wpa_supplicant(ssid, psk):
#     wpa_supplicant_path = "/etc/wpa_supplicant/wpa_supplicant.conf"

#     with open(wpa_supplicant_path, "a") as f:
#         f.write(f'\nnetwork={{\nssid="{ssid}"\npsk="{psk}"\n}}\n')

#     subprocess.call(["sudo", "systemctl", "daemon-reload"])
#     subprocess.call(["sudo", "systemctl", "restart", "dhcpcd"])


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

    wifi = check_internet()
    if not wifi:
        _LOGGER.error("No internet connection for TTS")
        exit

    # Check internet connection
    # while not wifi:
    #     time.sleep(2)
    #     ssid = get_user_input("wifi SSID:")
    #     psk = get_user_input("wifi PSK:")
    #     update_wpa_supplicant(ssid, psk)
    #     time.sleep(5)
    #     wifi = check_internet()
    #     time.sleep(2)

    loop = Loop()
    loop.preload()

    save_thread = threading.Thread(
        target=loop.player.periodic_save, args=(300,), daemon=True
    )
    save_thread.start()

    loop.loop()
