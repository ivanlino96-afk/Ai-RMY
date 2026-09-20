"""pyserial client talking to the ESP32 gimbal controller.

Handles the two realities of a USB-serial link to a microcontroller that
this module owns end to end:
  - the device node can disappear (unplug, ESP32 reset, Jetson reboot) and
    must be reconnected with backoff instead of raising forever.
  - reads/writes happen from a dedicated background thread so the caller
    (the tracking loop) never blocks on serial I/O.

Firmware is the safety authority (soft limits, watchdog) — this client
only forwards commands and parses whatever telemetry comes back.
"""

import logging
import threading
import time

import serial

from vision.config import SerialLinkConfig
from vision.serial_link.protocol import (
    encode_goto,
    encode_home,
    encode_move_delta,
    encode_ping,
    encode_stop,
    parse_telemetry,
)

logger = logging.getLogger(__name__)


class SerialLink(object):
    """Thread-safe client. Call start()/stop() around use."""

    def __init__(self, config=None, on_telemetry=None):
        self._config = config or SerialLinkConfig()
        self._on_telemetry = on_telemetry
        self._serial = None
        self._write_lock = threading.Lock()
        self._seq = 0
        self._stop_event = threading.Event()
        self._thread = None
        self._connected = False
        self.last_telemetry = None

    @property
    def connected(self):
        return self._connected

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="serial-link", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._close()

    def send_move_delta(self, pan, tilt):
        self._send(encode_move_delta(pan, tilt, self._next_seq()))

    def send_goto(self, pan_deg, tilt_deg):
        self._send(encode_goto(pan_deg, tilt_deg, self._next_seq()))

    def send_stop(self):
        self._send(encode_stop(self._next_seq()))

    def send_home(self):
        self._send(encode_home(self._next_seq()))

    def send_ping(self):
        self._send(encode_ping(self._next_seq()))

    def _next_seq(self):
        self._seq += 1
        return self._seq

    def _send(self, line):
        with self._write_lock:
            if self._serial is None:
                return False
            try:
                self._serial.write(line.encode("utf-8"))
                return True
            except (serial.SerialException, OSError):
                self._mark_disconnected()
                return False

    def _run(self):
        backoff = list(self._config.reconnect_backoff_s)
        attempt = 0
        last_ping = 0.0

        while not self._stop_event.is_set():
            if self._serial is None:
                if not self._connect():
                    delay = backoff[min(attempt, len(backoff) - 1)]
                    attempt += 1
                    self._stop_event.wait(delay)
                    continue
                attempt = 0

            try:
                line = self._serial.readline()
            except (serial.SerialException, OSError):
                self._mark_disconnected()
                continue

            if line:
                telemetry = parse_telemetry(line.decode("utf-8", errors="ignore"))
                if telemetry is not None:
                    self.last_telemetry = telemetry
                    if self._on_telemetry is not None:
                        self._on_telemetry(telemetry)

            now = time.monotonic()
            if now - last_ping >= self._config.ping_interval_s:
                self.send_ping()
                last_ping = now

    def _connect(self):
        try:
            self._serial = serial.Serial(
                self._config.port,
                self._config.baudrate,
                timeout=self._config.read_timeout_s,
            )
            self._connected = True
            logger.info("serial link connected on %s", self._config.port)
            return True
        except (serial.SerialException, OSError) as exc:
            logger.warning("serial connect failed on %s: %s", self._config.port, exc)
            self._serial = None
            self._connected = False
            return False

    def _mark_disconnected(self):
        logger.warning("serial link lost, will retry")
        self._close()

    def _close(self):
        if self._serial is not None:
            try:
                self._serial.close()
            except (serial.SerialException, OSError):
                pass
        self._serial = None
        self._connected = False
