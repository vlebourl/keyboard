import argparse
import logging
import os
import platform
import threading

import requests
from audio import GoogleTTS, PiperTTS, PygameMP3Player
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


_BOOTSTRAP_PROMPTS = {
    "tts_choice": "Appuyez sur 1 pour la voix locale, ou sur 2 pour la voix internet.",
    "no_internet": "Pas de connexion internet. La voix locale sera utilisée.",
}

_BOOTSTRAP_SOUNDS_DIR = "sounds/bootstrap"


def _ensure_bootstrap_audio():
    """Pre-generate bootstrap prompts with piper so they're always available."""
    os.makedirs(_BOOTSTRAP_SOUNDS_DIR, exist_ok=True)
    try:
        piper = PiperTTS()
        for key, text in _BOOTSTRAP_PROMPTS.items():
            path = os.path.join(_BOOTSTRAP_SOUNDS_DIR, f"{key}.wav")
            if not os.path.isfile(path):
                _LOGGER.info("Generating bootstrap audio: %s", key)
                audio = piper.generate(text)
                if audio:
                    with open(path, "wb") as f:
                        f.write(audio)
    except Exception as e:
        _LOGGER.warning("Could not pre-generate bootstrap audio: %s", e)


def _play_bootstrap(player, key):
    path = os.path.join(_BOOTSTRAP_SOUNDS_DIR, f"{key}.wav")
    if os.path.isfile(path):
        player.play_mp3_file(path)
    else:
        _LOGGER.warning("Bootstrap audio missing: %s", path)


if __name__ == "__main__":
    _LOGGER.info("Starting talking keyboard")

    keyboard = Keyboard()

    # Bootstrap player uses piper regardless of later TTS choice
    bootstrap_player = PygameMP3Player(tts=PiperTTS())
    _ensure_bootstrap_audio()

    wifi = check_internet()

    if wifi:
        _play_bootstrap(bootstrap_player, "tts_choice")
        key = keyboard.get_one_letter()
        tts = PiperTTS() if key == "1" else GoogleTTS()
        _LOGGER.info("TTS engine selected: %s", type(tts).__name__)
    else:
        _LOGGER.warning("No internet — defaulting to local TTS (piper)")
        _play_bootstrap(bootstrap_player, "no_internet")
        tts = PiperTTS()

    loop = Loop(keyboard=keyboard, tts=tts)
    loop.preload()

    save_thread = threading.Thread(
        target=loop.player.periodic_save, args=(300,), daemon=True
    )
    save_thread.start()

    loop.loop()
