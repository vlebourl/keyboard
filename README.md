# Talking Keyboard

A Python application that voices keyboard input, primarily designed for accessibility and potentially for language learning purposes. It captures keystrokes and converts them into spoken words in real-time.

## Features

*   **Real-time Text-to-Speech:** Typed characters and completed words are immediately spoken.
*   **French Language Support:** Includes specific logic for converting numbers to words in French (Swiss convention, with "huitante" corrected to "quatre-vingt").
*   **Audio Caching:** Frequently used words and individual letters are cached as MP3 files to improve performance and minimize reliance on the TTS service.
*   **Adaptive Keyboard Input:** Automatically selects the appropriate keyboard input library:
    *   `evdev` for headless Linux environments (e.g., Raspberry Pi running directly on the console).
    *   `pynput` for desktop environments (Windows, macOS, and Linux with a display server).
*   **Sound Preloading:** Common letter sounds are preloaded at startup for a faster initial response.
*   **Adjustable Logging:** Supports configurable log levels via command-line arguments for debugging.

## Requirements

*   Python 3.x
*   An active internet connection (for the initial generation of audio files using Google TTS).
*   The Python packages listed in `requirements.txt`.
*   On Linux, you might need `espeak` or `festival` for gTTS, and for Pygame audio, you might need libraries like `libsdl2-mixer-2.0-0`.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd talking-keyboard
    ```
2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Install system dependencies (Linux):**
    For Pygame audio, you might need to install SDL2 mixer libraries. For example, on Debian/Ubuntu:
    ```bash
    sudo apt-get update
    sudo apt-get install libsdl2-mixer-2.0-0
    ```
    For gTTS, ensure you have a text-to-speech engine like `espeak` or `festival` installed if you encounter issues:
    ```bash
    sudo apt-get install espeak
    ```

## Usage

1.  **Run the application:**
    ```bash
    python talking_keyboard/main.py
    ```
2.  **Command-line arguments:**
    *   `--loglevel LEVEL`: Set the logging level. `LEVEL` can be `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Defaults to `WARNING`.
    Example:
    ```bash
    python talking_keyboard/main.py --loglevel DEBUG
    ```
3.  **Exiting the application:**
    Type `exitnowarn` and press Enter. The application will close without playing the word "exitnowarn".

## Keyboard Input Libraries

The application uses different libraries for capturing keyboard input depending on the environment:
*   **`python-evdev`**: Used on Linux systems when no display server (like X11) is detected. This is common for devices running in console mode. It requires read access to `/dev/input/event*` devices.
*   **`pynput`**: Used on Windows, macOS, and Linux systems with a display server. It generally works out-of-the-box in most desktop environments.

## Future Enhancements

*   **Wi-Fi Configuration:** The codebase contains commented-out functionality for setting up Wi-Fi connections. This could be developed into a user-friendly feature for headless devices.
*   **Multi-language Support:** Extend TTS and number conversion to support other languages.
*   **Customizable Voice:** Allow users to select different TTS voices or engines.

## Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes.
4.  Add tests for your changes if applicable.
5.  Submit a pull request with a clear description of your changes.

## License

This project is licensed under the GNU General Public License v2.0. See the `LICENSE` file for the full license text.
