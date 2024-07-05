import logging

try:
    from RPLCD.i2c import CharLCD

    lcd_available = True
except ImportError:
    lcd_available = False

_LOGGER = logging.getLogger(__name__)


class LCDDisplay:
    COLS = 16
    ROWS = 2

    def __init__(self):
        if lcd_available:
            self.lcd = CharLCD(
                i2c_expander="PCF8574",
                address=0x27,
                port=1,
                cols=self.COLS,
                rows=self.ROWS,
                dotsize=8,
            )
        else:
            self.lcd = None
        self.buffer = ["", ""]
        if self.lcd:
            self.lcd.clear()
            self.lcd.cursor_pos = (1, 0)

    def _write_buffer(self):
        if not self.lcd:
            return
        self.lcd.clear()
        for i in [0, 1]:
            self.lcd.cursor_pos = (i, 0)
            self.lcd.write_string(self.buffer[i])
            _LOGGER.debug(f"writing: '{self.buffer[i]}'")

    def get_buffer(self):
        return self.buffer

    def write_words(self, word1, word2):
        if not self.lcd:
            return
        self.buffer[0] = word1[:16]
        self.buffer[1] = word2[:16]
        self._write_buffer()

    def add_letter(self, letter):
        if not self.lcd:
            return
        current_line = self.buffer[1]
        _LOGGER.debug(f"cursor: {self.lcd.cursor_pos}")
        if len(current_line) < self.COLS:
            current_line += letter
        else:
            current_line = current_line[1:] + letter
        self.buffer[1] = current_line
        self._write_buffer()

    def move_row_up(self):
        if not self.lcd:
            return
        _LOGGER.debug(f"buffer: {self.buffer}")
        self.buffer[0] = self.buffer[1]
        self.buffer[1] = ""
        _LOGGER.debug(f"new buffer: {self.buffer}")
        self._write_buffer()

    def clear(self):
        if not self.lcd:
            return
        self.lcd.clear()
        self.buffer = ["", ""]
