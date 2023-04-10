# Talking Keyboard

This program implements a talking keyboard that reads aloud the typed characters and words. The application uses either Google Text-to-Speech API or the Pico TTS system to generate speech based on the user's input.

## Dependencies

- Python 3.6 or higher
- simpleaudio
- gtts (Google Text-to-Speech)
- Pico TTS (available on Linux systems)

## Installation

1. Install Python 3.6 or higher if not already installed.
2. Install the required Python packages using pip:

```
pip install simpleaudio gtts
```

3. Install Pico TTS on your Linux system (if available). Follow the instructions specific to your distribution.

## Usage

1. Run the script using the following command:

```
python talking_keyboard.py
```

2. Type characters on the keyboard, and the program will play the corresponding sounds for each character and word.

3. The program will preload the most common letters for faster response time.

4. The program will periodically save common words to a pickle file, which will be loaded upon startup to improve performance.

## Customization

You can customize the language by changing the `VOICES` list and the default language in the `TTS` class initialization. The program will automatically use Google TTS if an internet connection is available; otherwise, it will use Pico TTS.

## License

This project is released under the MIT License.
