import contextlib
import io
import socket
import subprocess
import sys
import tempfile
import termios
import time
import wave

import pyaudio
import pygame.mixer
from gtts import gTTS

VOICES = ["de-DE", "en-GB", "en-US", "es-ES", "fr-FR", "it-IT"]


class PicoTTS:
    def __init__(self, voice="en-US"):
        self._voice = voice

    def generate(self, txt):
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            args = ["pico2wave", "-l", self._voice, "-w", f.name, txt]
            subprocess.run(args, check=True)
            f.seek(0)
            wav = f.read()
        return wav

    def set_voice(self, v):
        self._voice = v


class GoogleTTS:
    def __init__(self, language="fr"):
        self._language = language[:2]

    def set_voice(self, language):
        self._language = language[:2]

    def generate(self, text):
        tts = gTTS(text=text, lang=self._language)
        file = io.BytesIO()
        tts.write_to_fp(file)
        return file.getvalue()


class TTS:
    def __init__(self, internet=False, language="fr-FR"):
        self.tts = GoogleTTS(language) if internet else PicoTTS(language)

    def generate(self, text):
        return self.tts.generate(text)


class WavePlayer:
    def __init__(self, internet=False):
        self._internet = internet
        if self._internet:
            pygame.mixer.init()
            self.player = pygame.mixer
        else:
            self.player = pyaudio.PyAudio()

    def open_wave_string_and_play(self, wave_string):
        if self._internet:
            self.player.music.load(wave_string, "mp3")
            self.player.music.play()
            while self.player.music.get_busy():
                time.sleep(0.01)
        else:
            with wave.open(io.BytesIO(wave_string), "rb") as wave_file:
                stream = self.player.open(
                    format=self.player.get_format_from_width(wave_file.getsampwidth()),
                    channels=wave_file.getnchannels(),
                    rate=wave_file.getframerate(),
                    output=True,
                )

                data = wave_file.readframes(1024)
                while data:
                    stream.write(data)
                    data = wave_file.readframes(1024)

                stream.close()

    def close(self):
        if not self._internet:
            self.player.terminate()


def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        termios.tcsetattr(fd, termios.TCSAFLUSH, old_settings)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


class Keyboard:
    def __init__(self, internet=False):
        self.player = WavePlayer(internet)
        self.tts = TTS(internet)
        self.word = ""

    def get_one_letter(self):
        return getch()

    def process_letter(self, letter: str) -> None:
        if letter in {"\n", " ", "\r"}:
            if self.word:
                self.player.open_wave_string_and_play(self.tts.generate(self.word))
                self.word = ""
            return
        if not letter.isalnum():
            return
        self.word += letter
        self.player.open_wave_string_and_play(self.tts.generate(f" {letter} "))

    def loop(self):
        letter = self.get_one_letter()
        while True:
            self.process_letter(letter)
            letter = self.get_one_letter()


def internet_on():
    with contextlib.suppress(Exception):
        host = socket.gethostbyname("www.google.com")
        socket.create_connection((host, 80), 2)
        return True
    return False


if __name__ == "__main__":
    internet = internet_on()
    keyboard = Keyboard(internet)
    keyboard.word = "Bonjour, bienvenue sur le clavier parlant."
    if internet:
        keyboard.word += " Internet actif."
    keyboard.process_letter("\n")
    keyboard.loop()
