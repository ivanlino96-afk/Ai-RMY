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
                float panStepsPerDegree, float tiltStepsPerDegree, unsigned long watchdogTimeoutMs = 750);

  void begin();
  bool setStepLimits(long panMin, long panMax, long tiltMin, long tiltMax);
  bool setSpeeds(long pan, long tilt);
  bool setAccelerations(long pan, long tilt);
  long currentPanSteps() { return panStepper_.currentPosition(); }
  long currentTiltSteps() { return tiltStepper_.currentPosition(); }
  bool applySteps(long pan, long tilt, long panMin = 0, long panMax = 12000, long tiltMin = -1500, long tiltMax = 1500);

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

  // No limit switches: this re-defines the current physical position as the
  // new (0,0) origin. Does not move any motor. Called at boot (the power-on
  // position is the origin by definition) and on demand via the `home`
  // command / UI button, e.g. after a manual repositioning.
  void home();

  // Resets the watchdog timer. Call whenever a valid command is parsed,
  // even a `ping`.
  void noteCommandReceived();

  bool watchdogTripped() const;
  // Not const: AccelStepper::currentPosition()/distanceToGo() aren't
  // const-qualified upstream, even though these are pure reads.
  float currentPanDeg();
  float currentTiltDeg();
  bool isMoving();
  // True once an origin has been established. Set in begin() (the power-on
  // position counts as home) and stays true across explicit home() calls --
  // this is a relative, user-chosen reference, never an absolute calibrated
  // position (no limit switches).
  bool homed() const { return homed_; }

 private:
  AccelStepper panStepper_;
  AccelStepper tiltStepper_;
  GimbalLimits limits_;
  float panStepsPerDegree_;
  float tiltStepsPerDegree_;
  unsigned long watchdogTimeoutMs_;
  unsigned long lastCommandMs_ = 0;
  bool homed_ = false;

  long degToSteps(float deg, float scale) const;
  float stepsToDeg(long steps, float scale) const;
};
