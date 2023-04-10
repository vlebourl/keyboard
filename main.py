import io
import json
import logging
import socket
import sys
import tempfile
import termios
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pydub import AudioSegment
from pydub.playback import play
from gtts import gTTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

VOICES = ["de-DE", "en-GB", "en-US", "es-ES", "fr-FR", "it-IT"]

COMMON_WORDS_FILE = "common_words.json"


def preload_sounds_parallel(keyboard, letters):
    """
    Preload sounds for given letters using multiple threads.

    :param keyboard: Keyboard object
    :param letters: List of letters for which sounds will be preloaded
    """
    with ThreadPoolExecutor() as executor:
        executor.map(keyboard.player.preload_sound, letters)


class GoogleTTS:
    """
    Wrapper around Google Text-to-Speech API.
    """

    def __init__(self, language="fr"):
        """
        Initialize GoogleTTS with a language.

        :param language: A string representing the language (default: "fr")
        """
        self._language = language[:2]

    def set_voice(self, language):
        """
        Set the voice language for Google TTS.

        :param language: A string representing the voice language
        """
        self._language = language[:2]

    def generate(self, text):
        """
        Generate MP3 data for the given text using Google TTS API.

        :param text: The text to be converted to speech
        :return: The MP3 data as bytes
        """
        tts = gTTS(text=text, lang=self._language)
        file = io.BytesIO()
        tts.write_to_fp(file)
        return file.getvalue()


class PydubMP3Player:
    """
    Class responsible for playing and managing the MP3 data using pydub.playback.
    """

    def __init__(self, tts):
        """
        Initialize PydubMP3Player with the given TTS system.

        :param tts: An instance of GoogleTTS class
        """
        self.tts = tts
        self.generated_words = {}
        self.word_count = {}

        self.load_common_words()

    def preload_sound(self, text):
        """
        Preload sound for the given text.

        :param text: The text to be preloaded
        """
        mp3_data = self.tts.generate(text)
        self.generated_words[text] = mp3_data

    def open_mp3_string_and_play(self, text, mp3_data=None):
        """
        Play the sound associated with the given text.

        :param text: The text whose sound will be played
        :param mp3_data: Optional MP3 data as bytes, if available
        """
        if text in self.generated_words:
            mp3_data = self.generated_words[text]
        else:
            if mp3_data is None:
                mp3_data = self.tts.generate(text)
            self.generated_words[text] = mp3_data

        audio_segment = AudioSegment.from_file(io.BytesIO(mp3_data), format="mp3")
        play(audio_segment)

        self.word_count[text] = self.word_count.get(text, 0) + 1
        if self.word_count[text] >= 2:
                        self.generated_words[text] = mp3_data

    def load_common_words(self):
        """
        Load common words from the JSON file, if available.
        """
        with contextlib.suppress(FileNotFoundError):
            with open(COMMON_WORDS_FILE, "r") as f:
                self.generated_words = {k: bytes.fromhex(v) for k, v in json.load(f).items()}

    def save_common_words(self):
        """
        Save common words to the JSON file.
        """
        with open(COMMON_WORDS_FILE, "w") as f:
            json.dump({k: v.hex() for k, v in self.generated_words.items()}, f)

    def periodic_save(self, interval):
        """
        Periodically save common words to the json file.

        :param interval: Time interval in seconds between saves
        """
        while True:
            time.sleep(interval)
            self.save_common_words()


class Keyboard:
    """
    Class responsible for handling user input and playing corresponding sounds.
    """

    def __init__(self):
        """
        Initialize Keyboard.
        """
        self.tts = GoogleTTS()
        self.player = PydubMP3Player(self.tts)
        self.word = ""

    def get_one_letter(self):
        """
        Get one letter of user input.

        :return: A string containing one letter
        """
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            new_settings = termios.tcgetattr(fd)
            new_settings[3] = new_settings[3] & ~termios.ICANON & ~termios.ECHO
            termios.tcsetattr(fd, termios.TCSAFLUSH, new_settings)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def process_letter(self, letter: str) -> None:
        """
        Process one letter of user input and play the corresponding sound.

        :param letter: A string containing one letter
        """
        if letter in {"\n", " ", "\r"}:
            if self.word:
                logging.info("playing word: %s", self.word)
                self.player.open_mp3_string_and_play(self.word)
                self.word = ""
            return
        if not letter.isalnum():
            return
        self.word += letter
        self.player.open_mp3_string_and_play(f" {letter} ")

    def loop(self):
        """
        Start the main loop to process user input and play sounds.
        """
        letter = self.get_one_letter()
        while True:
            self.process_letter(letter)
            letter = self.get_one_letter()


if __name__ == "__main__":
    logging.info("Starting talking keyboard")

    keyboard = Keyboard()

    # Preload most common letters
    common_letters = "abcdefghijklmnopqrstuvwxyz1234567890"
    logging.info("Preloading common letters")
    for letter in common_letters:
        if f" {letter} " not in keyboard.player.generated_words:
            logging.info("    Preloading letter: %s", letter)
            keyboard.player.preload_sound(f" {letter} ")
    keyboard.player.save_common_words()

    logging.info("Preloaded words are:")
    for word in keyboard.player.generated_words.keys():
        logging.info("    %s", word)

    keyboard.word = "Bonjour, bienvenue sur le clavier parlant."
    keyboard.process_letter("\n")

    # Launch a new thread to periodically save common words
    save_thread = threading.Thread(
        target=keyboard.player.periodic_save, args=(300,), daemon=True
    )
    save_thread.start()

    logging.info("Entering main loop")

    keyboard.loop()
