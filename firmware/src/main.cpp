#include <Arduino.h>

#include <string>

#include "GimbalControl.h"
#include "SerialProtocol.h"

// Arduino Uno (ATmega328P), per docs/hardware-wiring.md. D0/D1 are reserved
// for the hardware UART (USB Serial link to the Jetson) and D13 is tied to
// the onboard LED/SPI SCK (avoided to prevent a boot-time glitch) — neither
// is used for STEP/DIR/ENABLE.
static const uint8_t kPanStepPin = 2;
static const uint8_t kPanDirPin = 3;
static const uint8_t kTiltStepPin = 4;
static const uint8_t kTiltDirPin = 5;

// TODO(hardware-wiring.md): depends on TB6600 microstepping DIP switches and
// motor step angle. Placeholder assumes 200 full steps/rev * 1/8 microstepping
// = 1600 steps/rev -> 1600/360 steps per degree.
static const float kStepsPerDegree = 1600.0f / 360.0f;

// Conservative placeholder soft limits — widen only after bench testing at
// low speed (see AGENTS.md).
static const GimbalLimits kLimits = {-45.0f, 45.0f, -30.0f, 30.0f};

static const unsigned long kTelemetryIntervalMs = 100;  // ~10 Hz

// Watchdog above SerialLink's ping_interval_s (2.0s, see
// vision/src/vision/config.py) so the periodic keep-alive ping actually
// prevents a false trip during normal idle gaps or a single long manual jog.
GimbalControl gimbal(kPanStepPin, kPanDirPin, kTiltStepPin, kTiltDirPin,
                     kLimits, kStepsPerDegree, /*watchdogTimeoutMs=*/3000);

unsigned long lastTelemetryMs = 0;
std::string serialBuffer;

void sendTelemetry(bool ok, long seq, const char *error = nullptr) {
  std::string line = serializeTelemetry(ok, seq, gimbal.currentPanDeg(),
                                         gimbal.currentTiltDeg(),
                                         gimbal.isMoving(), gimbal.homed(),
                                         error);
  Serial.println(line.c_str());
}

void handleLine(const std::string &line) {
  Command cmd;
  if (!parseCommand(line, cmd)) {
    sendTelemetry(false, 0, "malformed_or_unknown_command");
    return;
  }

  gimbal.noteCommandReceived();

  switch (cmd.type) {
    case CommandType::MoveDelta:
      gimbal.applyDelta(cmd.pan, cmd.tilt);
      sendTelemetry(true, cmd.seq);
      break;
    case CommandType::Goto:
      gimbal.applyGoto(cmd.pan, cmd.tilt);
      sendTelemetry(true, cmd.seq);
      break;
    case CommandType::Stop:
      gimbal.stop();
      sendTelemetry(true, cmd.seq);
      break;
    case CommandType::Home:
      // No limit switches: re-defines the current physical position as the
      // new (0,0) origin. Does not move any motor.
      gimbal.home();
      sendTelemetry(true, cmd.seq);
      break;
    case CommandType::Ping:
      sendTelemetry(true, cmd.seq);
      break;
    default:
      sendTelemetry(false, cmd.seq, "unknown_command");
      break;
  }
}

void setup() {
  Serial.begin(115200);
  gimbal.begin();
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      handleLine(serialBuffer);
      serialBuffer = "";
    } else if (c != '\r') {
      serialBuffer += c;
    }
  }

  gimbal.update();

  unsigned long now = millis();
  if (now - lastTelemetryMs >= kTelemetryIntervalMs) {
    lastTelemetryMs = now;
    sendTelemetry(true, 0);  // seq=0 marks unsolicited periodic telemetry
  }
}
