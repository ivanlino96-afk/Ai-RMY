#include <Arduino.h>

#include <string>

#include "GimbalControl.h"
#include "SerialProtocol.h"

// TODO(hardware-wiring.md): placeholder pins — update once the ESP32 board
// and driver wiring are finalized. Do not wire real motors against these
// without checking docs/hardware-wiring.md first.
static const uint8_t kPanStepPin = 25;
static const uint8_t kPanDirPin = 26;
static const uint8_t kTiltStepPin = 27;
static const uint8_t kTiltDirPin = 14;

// TODO(hardware-wiring.md): depends on TB660 microstepping DIP switches and
// motor step angle. Placeholder assumes 200 full steps/rev * 1/8 microstepping
// = 1600 steps/rev -> 1600/360 steps per degree.
static const float kStepsPerDegree = 1600.0f / 360.0f;

// Conservative placeholder soft limits — widen only after bench testing at
// low speed (see AGENTS.md).
static const GimbalLimits kLimits = {-45.0f, 45.0f, -30.0f, 30.0f};

static const unsigned long kTelemetryIntervalMs = 100;  // ~10 Hz

GimbalControl gimbal(kPanStepPin, kPanDirPin, kTiltStepPin, kTiltDirPin,
                     kLimits, kStepsPerDegree);

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
      // Reserved: no limit switches in the MVP. Ack without acting.
      sendTelemetry(true, cmd.seq, "home_not_implemented");
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
