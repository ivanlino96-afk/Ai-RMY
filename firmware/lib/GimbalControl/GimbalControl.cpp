#include "GimbalControl.h"

GimbalControl::GimbalControl(uint8_t panStepPin, uint8_t panDirPin,
                              uint8_t tiltStepPin, uint8_t tiltDirPin,
                              GimbalLimits limits, float stepsPerDegree,
                              unsigned long watchdogTimeoutMs)
    : panStepper_(AccelStepper::DRIVER, panStepPin, panDirPin),
      tiltStepper_(AccelStepper::DRIVER, tiltStepPin, tiltDirPin),
      limits_(limits),
      stepsPerDegree_(stepsPerDegree),
      watchdogTimeoutMs_(watchdogTimeoutMs) {}

void GimbalControl::begin() {
  // Conservative defaults — tune once real motors/drivers are on the bench.
  // See AGENTS.md: test at low speed with conservative limits first.
  panStepper_.setMaxSpeed(800);
  panStepper_.setAcceleration(400);
  tiltStepper_.setMaxSpeed(800);
  tiltStepper_.setAcceleration(400);
  lastCommandMs_ = millis();
}

void GimbalControl::update() {
  if (watchdogTripped()) {
    // No valid command recently: hold position, do not keep extrapolating.
    panStepper_.stop();
    tiltStepper_.stop();
  }
  panStepper_.run();
  tiltStepper_.run();
}

void GimbalControl::applyDelta(float panDeg, float tiltDeg) {
  float targetPan = clampDeg(currentPanDeg() + panDeg, limits_.panMinDeg, limits_.panMaxDeg);
  float targetTilt = clampDeg(currentTiltDeg() + tiltDeg, limits_.tiltMinDeg, limits_.tiltMaxDeg);
  panStepper_.moveTo(degToSteps(targetPan));
  tiltStepper_.moveTo(degToSteps(targetTilt));
}

void GimbalControl::applyGoto(float panDeg, float tiltDeg) {
  float targetPan = clampDeg(panDeg, limits_.panMinDeg, limits_.panMaxDeg);
  float targetTilt = clampDeg(tiltDeg, limits_.tiltMinDeg, limits_.tiltMaxDeg);
  panStepper_.moveTo(degToSteps(targetPan));
  tiltStepper_.moveTo(degToSteps(targetTilt));
}

void GimbalControl::stop() {
  panStepper_.stop();
  tiltStepper_.stop();
  panStepper_.setCurrentPosition(panStepper_.currentPosition());
  tiltStepper_.setCurrentPosition(tiltStepper_.currentPosition());
}

void GimbalControl::noteCommandReceived() { lastCommandMs_ = millis(); }

bool GimbalControl::watchdogTripped() const {
  return (millis() - lastCommandMs_) > watchdogTimeoutMs_;
}

float GimbalControl::currentPanDeg() { return stepsToDeg(panStepper_.currentPosition()); }
float GimbalControl::currentTiltDeg() { return stepsToDeg(tiltStepper_.currentPosition()); }

bool GimbalControl::isMoving() {
  return panStepper_.distanceToGo() != 0 || tiltStepper_.distanceToGo() != 0;
}

long GimbalControl::degToSteps(float deg) const { return lround(deg * stepsPerDegree_); }
float GimbalControl::stepsToDeg(long steps) const { return steps / stepsPerDegree_; }
