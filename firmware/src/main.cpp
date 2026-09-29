#include <Arduino.h>



#include "GimbalControl.h"
#include "SerialProtocol.h"

// Board-specific STEP/DIR pins. Uno D0/D1 are reserved for USB UART.
#if defined(ARDUINO_AVR_UNO)
static const uint8_t kPanStepPin = 2;
static const uint8_t kPanDirPin = 3;
static const uint8_t kTiltStepPin = 4;
static const uint8_t kTiltDirPin = 5;
#else
static const uint8_t kPanStepPin = 1;
static const uint8_t kPanDirPin = 2;
static const uint8_t kTiltStepPin = 3;
static const uint8_t kTiltDirPin = 4;
#endif

// Operator-measured transmission; Tilt is approximate, not encoder feedback.
static const float kPanStepsPerDegree = kPanTransmission;
static const float kTiltStepsPerDegree = kTiltTransmission;
static const GimbalLimits kLimits = {0.0f, 360.0f, -55.0f, 55.0f};

static const unsigned long kTelemetryIntervalMs = 100;  // ~10 Hz

// Watchdog above SerialLink's ping_interval_s (2.0s, see
// vision/src/vision/config.py) so the periodic keep-alive ping actually
// prevents a false trip during normal idle gaps or a single long manual jog.
GimbalControl gimbal(kPanStepPin, kPanDirPin, kTiltStepPin, kTiltDirPin,
                     kLimits, kPanStepsPerDegree, kTiltStepsPerDegree, /*watchdogTimeoutMs=*/3000);

#ifdef GIMBAL_CALIBRATION
static const bool kCalibration = true;
#else
static const bool kCalibration = false;
#endif
unsigned long lastTelemetryMs = 0;
ProtocolString serialBuffer;

void sendTelemetry(bool ok, long seq, const char *error = nullptr) {
#if defined(ARDUINO_ARCH_AVR)
  writeTelemetry(Serial, ok, seq, gimbal.currentPanDeg(), gimbal.currentTiltDeg(),
                 gimbal.isMoving(), gimbal.homed(), error, kCalibration,
                 gimbal.currentPanSteps(), gimbal.currentTiltSteps());
#else
  ProtocolString line = serializeTelemetry(ok, seq, gimbal.currentPanDeg(),
                                         gimbal.currentTiltDeg(),
                                         gimbal.isMoving(), gimbal.homed(),
                                         error, kCalibration, gimbal.currentPanSteps(), gimbal.currentTiltSteps());
  Serial.println(line.c_str());
#endif
}

void handleLine(const ProtocolString &line) {
  Command cmd;
  if (!parseCommand(line, cmd)) {
    sendTelemetry(false, 0, "malformed_or_unknown_command");
    return;
  }

  if (kCalibration && (cmd.type == CommandType::MoveDelta || cmd.type == CommandType::Goto)) {
    sendTelemetry(false, cmd.seq, "calibration_only");
    return;
  }
  if (cmd.type == CommandType::MoveSteps && gimbal.isMoving()) {
    sendTelemetry(false, cmd.seq, "steps_rejected");
    return;
  }
  if ((cmd.type == CommandType::MoveSteps || cmd.type == CommandType::MoveDelta || cmd.type == CommandType::Goto) &&
      !gimbal.setStepLimits(cmd.panMin, cmd.panMax, cmd.tiltMin, cmd.tiltMax)) {
    sendTelemetry(false, cmd.seq, "invalid_step_limits");
    return;
  }
  if (cmd.panSpeed && !gimbal.setSpeeds(cmd.panSpeed, cmd.tiltSpeed)) {
    sendTelemetry(false, cmd.seq, "invalid_speed");
    return;
  }
  if (cmd.panAccel && !gimbal.setAccelerations(cmd.panAccel, cmd.tiltAccel)) {
    sendTelemetry(false, cmd.seq, "invalid_acceleration");
    return;
  }
  gimbal.noteCommandReceived();

  switch (cmd.type) {
    case CommandType::MoveSteps: {
      bool ok = gimbal.applySteps(cmd.panSteps, cmd.tiltSteps, cmd.panMin, cmd.panMax, cmd.tiltMin, cmd.tiltMax);
      sendTelemetry(ok, cmd.seq, ok ? nullptr : "steps_rejected");
      break;
    }
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
