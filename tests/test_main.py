import unittest
from unittest.mock import MagicMock, patch

from talking_keyboard.audio import GoogleTTS, PygameMP3Player
from talking_keyboard.keyboard import Keyboard
from talking_keyboard.main import parse_arguments


class TestGoogleTTS(unittest.TestCase):
    def setUp(self):
        self.google_tts = GoogleTTS()

    def test_set_voice(self):
        self.google_tts.set_voice("en-US")
        self.assertEqual(self.google_tts._language, "en")


class TestPygameMP3Player(unittest.TestCase):
    def setUp(self):
        tts = MagicMock()
        self.mp3_player = PygameMP3Player(tts)

    def test_preload_sound(self):
        with patch("talking_keyboard.main.open", unittest.mock.mock_open()), patch.object(
            self.mp3_player.tts, "generate"
        ) as mock_generate:
            mock_generate.return_value = b"mp3_data"
            self.mp3_player.preload_sound("test")
            self.assertIn("test", self.mp3_player.generated_words)


class TestKeyboard(unittest.TestCase):
    def setUp(self):
        with patch("talking_keyboard.main.InputDevice") as mock_input_device:
            self.keyboard = Keyboard()
            self.mock_input_device = mock_input_device

    def test_set_volume(self):
        with patch.object(self.keyboard.mixer, "setvolume") as mock_setvolume:
            self.keyboard.set_volume(80)
            mock_setvolume.assert_called_once_with(80)

    def test_find_keyboard_device_path(self):
        with patch("talking_keyboard.main.glob.glob", return_value=["/dev/input/by-id/test-kbd"]):
            device_path = self.keyboard.find_keyboard_device_path()
            self.assertEqual(device_path, "/dev/input/by-id/test-kbd")


class TestMain(unittest.TestCase):
    def test_parse_arguments(self):
        args = parse_arguments(["--loglevel", "DEBUG"])
        self.assertEqual(args.loglevel, "DEBUG")

    def test_parse_arguments_invalid(self):
        with self.assertRaises(SystemExit):
            parse_arguments(["--loglevel", "INVALID"])


if __name__ == "__main__":
    unittest.main()
