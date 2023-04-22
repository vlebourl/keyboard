import logging
import secrets
import threading
import time

from rpi_ws281x import Color, PixelStrip

_LOGGER = logging.getLogger(__name__)


class LEDStrip:
    # LED strip configuration:
    LED_COUNT = 10  # Number of LED pixels.
    LED_PIN = 18  # GPIO pin connected to the pixels (must support PWM).
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10  # DMA channel to use for generating signal (try 10)
    LED_BRIGHTNESS = 40  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = (
        False  # True to invert the signal (when using NPN transistor level shift)
    )
    LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53

    OFF = Color(0, 0, 0)
    RED = Color(255, 0, 0)
    WHITE = Color(255, 255, 255)
    GREEN = Color(0, 255, 0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.led_strip:
            self.light_up(self.OFF)

    def __init__(self) -> None:
        try:
            # Create PixelStrip object
            self.stop_green_thread = threading.Event()
            self.led_strip = False

            self.strip = PixelStrip(
                self.LED_COUNT,
                self.LED_PIN,
                self.LED_FREQ_HZ,
                self.LED_DMA,
                self.LED_INVERT,
                self.LED_BRIGHTNESS,
                self.LED_CHANNEL,
            )
            # Initialize the library
            self.strip.begin()
            self.led_strip = True
        except RuntimeError:
            _LOGGER.warning("Could not initialize LED strip, skipping")

    def generate_color_map(self, key_map):
        return {
            v: [
                Color(
                    secrets.randbelow(256),
                    secrets.randbelow(256),
                    secrets.randbelow(256),
                )
                for _ in range(10)
            ]
            for v in key_map.values()
        }

    def light_up(self, color):
        for i in range(self.strip.numPixels()):
            if isinstance(color, list):
                self.strip.setPixelColor(i, color[i])
            else:
                self.strip.setPixelColor(i, color)
        self.strip.show()

    def _flash(self, color, flash_duration_ms):
        self.light_up(color)
        time.sleep(flash_duration_ms / 1000.0)

    def flash(self, color=RED, num_flashes=5, flash_duration_ms=50, do_stop=True):
        if not self.led_strip:
            return
        if do_stop:
            #global stop_green_thread  # Add this line to access the event
            self.stop_green_thread.set()  # Set the event to stop the green_thread
        for _ in range(num_flashes):
            self._flash(color, flash_duration_ms)
            self._flash(self.OFF, flash_duration_ms)

    def light_led_i(self, i, color, delay):
        self.strip.setPixelColor(i, color)
        self.strip.show()
        time.sleep(delay)

    def running_leds(self, color=GREEN, delay=0.5, stop_event=None):
        if not self.led_strip:
            return
        while not stop_event.is_set():
            for i in range(self.strip.numPixels()):
                self.light_led_i(i, color, delay)
            for i in range(self.strip.numPixels()):
                self.light_led_i(i, self.OFF, delay)
