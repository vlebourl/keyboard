# Talking Keyboard

This project implements a talking keyboard that audibly enunciates typed characters and words in real time. It is designed to work seamlessly on both Linux systems (using `evdev` when a display is not available) and environments with a GUI (using `pynput`).

## Features

- **Real-Time Audio Feedback:** Converts each typed character and assembled word into speech instantly.
- **Dual Input Support:**
  - **evdev:** For Linux systems without a graphical interface.
  - **pynput:** For systems running a GUI.
- **Intelligent TTS Selection:** Utilizes Google Text-to-Speech when an internet connection is available, and falls back to Pico TTS on Linux when offline.
- **Preloading Mechanism:** Preloads common letters for enhanced responsiveness.
- **Numeric Conversion:** Translates digit sequences into their word representation using `num2words`.
- **Periodic Persistence:** Automatically saves frequently used words to a file every 300 seconds.

## Requirements

- **Python:** Version 3.10 or higher
- **Dependencies:** Install the following Python packages:
  - `gtts`
  - `num2words`
  - `pygame`
  - `requests`
  - `pynput`
- **Optional (Linux):** For offline TTS, install Pico TTS (e.g., on Debian/Ubuntu: `sudo apt-get install libttspico-utils`)

## Installation

1. Clone the Repository:

```bash
git clone https://github.com/vlebourl/keyboard.git
cd keyboard
```

2.	Install Runtime Dependencies:

```bash
pip install -r requirements.txt
```
   
3.	Install Development Dependencies (Optional):

```bash
pip install -r requirements-dev.txt
```

## Usage

```bash
python talking_keyboard/main.py
```

### Environment Detection:
The application automatically detects whether to use evdev or pynput based on your system’s configuration.

## Customization

### Language & Voice Settings:
Modify the VOICES list and default language within the TTS class in talking_keyboard/audio.py to tailor the speech output.

### Preloading and Saving Interval:
Adjust the preloading mechanism and the periodic saving interval in the code if you desire a more tailored performance.

## License

This project is released under the MIT License.
