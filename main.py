import contextlib
import io
import logging
import pickle
import pygame
import socket
import subprocess
import sys
import tempfile
import termios
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pydub import AudioSegment
from gtts import gTTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

VOICES = ["de-DE", "en-GB", "en-US", "es-ES", "fr-FR", "it-IT"]

COMMON_WORDS_FILE = "common_words.pickle"


def preload_sounds_parallel(keyboard, letters):
    """
    Preload sounds for given letters using multiple threads.

    :param keyboard: Keyboard object
    :param letters: List of letters for which sounds will be preloaded
    """
    with ThreadPoolExecutor() as executor:
        executor.map(keyboard.player.preload_sound, letters)


class PicoTTS:
    """
    Wrapper around Pico TTS system.
    """

    def __init__(self, voice="en-US"):
        """
        Initialize PicoTTS with a voice.

        :param voice: A string representing the voice language (default: "en-US")
        """
        self._voice = voice

    def generate(self, txt):
        """
        Generate WAV data for the given text using Pico TTS.

        :param txt: The text to be converted to speech
        :return: The WAV data as bytes
        """
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            args = ["pico2wave", "-l", self._voice, "-w", f.name, txt]
            subprocess.run(args, check=True)
            f.seek(0)
            wav = f.read()
        return wav

    def set_voice(self, v):
        """
        Set the voice language for Pico TTS.

        :param v: A string representing the voice language
        """
        self._voice = v


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
        Generate WAV data for the given text using Google TTS API.

        :param text: The text to be converted to speech
        :return: The WAV data as bytes
        """
        tts = gTTS(text=text, lang=self._language)
        file = io.BytesIO()
        tts.write_to_fp(file)
        return file.getvalue()


class TTS:
    """
    Text-to-Speech class that supports both PicoTTS and GoogleTTS.
    """

    def __init__(self, internet=False, language="fr-FR"):
        """
        Initialize TTS with the given settings.

        :param internet: If True, use GoogleTTS, otherwise use PicoTTS (default: False)
        :param language: A string representing the language (default: "fr-FR")
        """
        self.tts = GoogleTTS(language) if internet else PicoTTS(language)

    def generate(self, text):
        """
        Generate WAV data for the given text using the selected TTS system.

        :param text: The text to be converted to speech
                :return: The WAV data as bytes
        """
        return self.tts.generate(text)


class PygameWavePlayer:
    """
    Class responsible for playing and managing the WAV data using pygame.mixer.
    """

    def __init__(self, tts, internet=False):
        """
        Initialize PygameWavePlayer with the given TTS system and settings.

        :param tts: An instance of TTS class
        :param internet: If True, use GoogleTTS, otherwise use PicoTTS (default: False)
        """
        self.tts = tts
        self._internet = internet
        self.generated_words = {}
        self.word_count = {}

        pygame.mixer.init()

        if internet:
            self.load_common_words()

    def preload_sound(self, text):
        """
        Preload sound for the given text.

        :param text: The text to be preloaded
        """
        wav = self.tts.generate(text)
        audio_segment = AudioSegment.from_file(io.BytesIO(wav), format="mp3")
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        self.generated_words[text] = wav_io.read()

    def open_wave_string_and_play(self, text, wave_string=None):
        """
        Play the sound associated with the given text.

        :param text: The text whose sound will be played
        :param wave_string: Optional WAV data as bytes, if available
        """
        if text in self.generated_words:
            wav_data = self.generated_words[text]
        else:
            if wave_string is None:
                wave_string = self.tts.generate(text)
            audio_segment = AudioSegment.from_file(io.BytesIO(wave_string), format="mp3")
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_io.seek(0)
            wav_data = wav_io.read()
            self.generated_words[text] = wav_data
        sound = pygame.mixer.Sound(io.BytesIO(wav_data))
        sound.play()

        self.word_count[text] = self.word_count.get(text, 0) + 1
        if self.word_count[text] >= 2:
            self.generated_words[text] = wav_data


    def load_common_words(self):
        """
        Load common words from the pickle file, if available.
        """
        # suppress FileNotFoundError if the pickle file does not exist
        # suppress EOFError if the pickle file is empty
        with contextlib.suppress(FileNotFoundError, EOFError):
            with open(COMMON_WORDS_FILE, "rb") as f:
                self.generated_words = pickle.load(f)

    def save_common_words(self):
        """
        Save common words to the pickle file.
        """
        with open(COMMON_WORDS_FILE, "wb") as f:
            # log the number of words saved
            logging.info("Saving %d words to %s", len(self.generated_words), COMMON_WORDS_FILE)
            pickle.dump(self.generated_words, f)

    def periodic_save(self, interval):
        """
        Periodically save common words to the pickle file.

        :param interval: Time interval in seconds between saves
        """
        while True:
            time.sleep(interval)
            self.save_common_words()

class Keyboard:
    """
    Class responsible for handling user input and playing corresponding sounds.
    """

    def __init__(self, internet=False):
        """
        Initialize Keyboard with the given settings.

        :param internet: If True, use GoogleTTS, otherwise use PicoTTS (default: False)
        """
        self.tts = TTS(internet)
        self.player = PygameWavePlayer(self.tts, internet)
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
                self.player.open_wave_string_and_play(
                    self.word
                )  # Pass the word without the wave_string
                self.word = ""
            return
        if not letter.isalnum():
            return
        self.word += letter
        self.player.open_wave_string_and_play(f" {letter} ")

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

    internet = False
    with contextlib.suppress(Exception):
        host = socket.gethostbyname("www.google.com")
        socket.create_connection((host, 80), 2)
        internet = True

    logging.info(f"Internet status: {internet}")


    keyboard = Keyboard(internet)

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

    if internet:
        keyboard.word += " Internet actif."
    keyboard.process_letter("\n")

    # Launch a new thread to periodically save common words
    save_thread = threading.Thread(
        target=keyboard.player.periodic_save, args=(300,), daemon=True
    )
    save_thread.start()

    logging.info("Entering main loop")

    keyboard.loop()
