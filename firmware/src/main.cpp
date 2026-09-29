#include <Arduino.h>

#include <string>

#include "GimbalControl.h"
#include "SerialProtocol.h"

// Arduino MKR Zero (SAMD21, ARM Cortex-M0+ @ 48MHz, 3.3V logic), per
// docs/hardware-wiring.md. Serial here is the native USB CDC port -- unlike
// the AVR Uno this replaced, D0/D1 have no hardware-UART role on this board
// (Serial1 lives on D13/D14 instead) and are free for STEP/DIR. D13/D14 are
// still avoided to keep Serial1 available if ever needed. These pins sink
// current (LOW = active pulse); PUL+/DIR+ of both TB6600 drivers are wired
// to the board's own +5V rail (see docs/hardware-wiring.md — the MKR Zero's
// ~7mA/pin limit isn't enough to source a 5V-opto input directly).
static const uint8_t kPanStepPin = 1;
static const uint8_t kPanDirPin = 2;
static const uint8_t kTiltStepPin = 3;
static const uint8_t kTiltDirPin = 4;

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
  Serial.begin(115200);  // baud is ignored on native USB CDC (SAMD21); kept for portability
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
