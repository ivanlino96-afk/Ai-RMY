#pragma once

#include <AccelStepper.h>
#include <Arduino.h>

#include "SoftLimits.h"

// Soft limits in degrees, relative to power-on position (0,0).
// No homing/limit switches in the MVP — see docs/hardware-wiring.md.
struct GimbalLimits {
  float panMinDeg;
  float panMaxDeg;
  float tiltMinDeg;
  float tiltMaxDeg;
};

// Wraps the 2 AccelStepper axes with soft-limit clamping and a command
// watchdog. This class is the firmware's safety authority: it must never
// trust that the host (Jetson) already validated a command.
class GimbalControl {
 public:
  GimbalControl(uint8_t panStepPin, uint8_t panDirPin, uint8_t tiltStepPin,
                uint8_t tiltDirPin, GimbalLimits limits,
                float stepsPerDegree, unsigned long watchdogTimeoutMs = 750);

  void begin();

  // Call every loop() iteration. Runs the steppers and, if the watchdog has
  // tripped (no valid command recently), holds the current position instead
  // of continuing to extrapolate motion.
  void update();

  // Incremental correction from the tracking loop. Clamped to soft limits.
  void applyDelta(float panDeg, float tiltDeg);

  // Absolute move (manual re-center). Clamped to soft limits.
  void applyGoto(float panDeg, float tiltDeg);

  // Highest priority: cancels any in-progress motion immediately.
  void stop();

  // Resets the watchdog timer. Call whenever a valid command is parsed,
  // even a `ping`.
  void noteCommandReceived();

  bool watchdogTripped() const;
  // Not const: AccelStepper::currentPosition()/distanceToGo() aren't
  // const-qualified upstream, even though these are pure reads.
  float currentPanDeg();
  float currentTiltDeg();
  bool isMoving();
  bool homed() const { return false; }  // reserved: no limit switches in MVP

 private:
  AccelStepper panStepper_;
  AccelStepper tiltStepper_;
  GimbalLimits limits_;
  float stepsPerDegree_;
  unsigned long watchdogTimeoutMs_;
  unsigned long lastCommandMs_ = 0;

  long degToSteps(float deg) const;
  float stepsToDeg(long steps) const;
};
