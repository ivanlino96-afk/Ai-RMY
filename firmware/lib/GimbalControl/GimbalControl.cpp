#include "GimbalControl.h"

GimbalControl::GimbalControl(uint8_t panStepPin, uint8_t panDirPin,
                              uint8_t tiltStepPin, uint8_t tiltDirPin,
                              GimbalLimits limits, float panStepsPerDegree, float tiltStepsPerDegree,
                              unsigned long watchdogTimeoutMs)
    : panStepper_(AccelStepper::DRIVER, panStepPin, panDirPin),
      tiltStepper_(AccelStepper::DRIVER, tiltStepPin, tiltDirPin),
      limits_(limits),
      panStepsPerDegree_(panStepsPerDegree),
      tiltStepsPerDegree_(tiltStepsPerDegree),
      watchdogTimeoutMs_(watchdogTimeoutMs) {}

void GimbalControl::begin() {
  // Conservative defaults — tune once real motors/drivers are on the bench.
  // See AGENTS.md: test at low speed with conservative limits first.
#ifdef GIMBAL_CALIBRATION
  const float maxSpeed = 160;
  const float acceleration = 400;
#else
  const float maxSpeed = 40;
  const float acceleration = 40;
#endif
  panStepper_.setMaxSpeed(maxSpeed);
  panStepper_.setAcceleration(acceleration);
  tiltStepper_.setMaxSpeed(maxSpeed);
  tiltStepper_.setAcceleration(acceleration);
  panStepper_.setMinPulseWidth(10);
  tiltStepper_.setMinPulseWidth(10);
  lastCommandMs_ = millis();
  // No limit switches: the position we power on at IS the origin.
  homed_ = true;
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
  panStepper_.moveTo(degToSteps(targetPan, panStepsPerDegree_));
  tiltStepper_.moveTo(degToSteps(targetTilt, tiltStepsPerDegree_));
}

void GimbalControl::applyGoto(float panDeg, float tiltDeg) {
  float targetPan = clampDeg(panDeg, limits_.panMinDeg, limits_.panMaxDeg);
  float targetTilt = clampDeg(tiltDeg, limits_.tiltMinDeg, limits_.tiltMaxDeg);
  panStepper_.moveTo(degToSteps(targetPan, panStepsPerDegree_));
  tiltStepper_.moveTo(degToSteps(targetTilt, tiltStepsPerDegree_));
}

void GimbalControl::stop() {
  panStepper_.stop();
  tiltStepper_.stop();
  panStepper_.setCurrentPosition(panStepper_.currentPosition());
  tiltStepper_.setCurrentPosition(tiltStepper_.currentPosition());
}

void GimbalControl::home() {
  panStepper_.stop();
  tiltStepper_.stop();
  panStepper_.setCurrentPosition(0);
  tiltStepper_.setCurrentPosition(0);
  homed_ = true;
}

void GimbalControl::noteCommandReceived() { lastCommandMs_ = millis(); }

bool GimbalControl::watchdogTripped() const {
  return (millis() - lastCommandMs_) > watchdogTimeoutMs_;
}

float GimbalControl::currentPanDeg() { return stepsToDeg(panStepper_.currentPosition(), panStepsPerDegree_); }
float GimbalControl::currentTiltDeg() { return stepsToDeg(tiltStepper_.currentPosition(), tiltStepsPerDegree_); }

bool GimbalControl::isMoving() {
  return panStepper_.distanceToGo() != 0 || tiltStepper_.distanceToGo() != 0;
}

long GimbalControl::degToSteps(float deg, float scale) const { return scaledSteps(deg, scale); }
float GimbalControl::stepsToDeg(long steps, float scale) const { return steps / scale; }

bool GimbalControl::applySteps(long pan, long tilt, long panMin, long panMax, long tiltMin, long tiltMax) {
  if (isMoving() || pan < -2000 || pan > 2000 || tilt < -2000 || tilt > 2000 ||
      (pan == 0) == (tilt == 0)) return false;
  long targetPan = currentPanSteps() + pan;
  long targetTilt = currentTiltSteps() + tilt;
  if (!validStepTarget(targetPan, targetTilt, panMin, panMax, tiltMin, tiltMax)) return false;
  panStepper_.moveTo(targetPan);
  tiltStepper_.moveTo(targetTilt);
  return true;
}

bool GimbalControl::setSpeeds(long pan, long tilt) {
  if (pan < 1 || pan > 4000 || tilt < 1 || tilt > 4000) return false;
  panStepper_.setMaxSpeed(pan);
  tiltStepper_.setMaxSpeed(tilt);
  return true;
}

bool GimbalControl::setAccelerations(long pan, long tilt) {
  if (pan < 1 || pan > 20000 || tilt < 1 || tilt > 20000) return false;
  panStepper_.setAcceleration(pan);
  tiltStepper_.setAcceleration(tilt);
  return true;
}


bool GimbalControl::setStepLimits(long panMin, long panMax, long tiltMin, long tiltMax) {
  if (!validStepTarget(currentPanSteps(), currentTiltSteps(), panMin, panMax, tiltMin, tiltMax)) return false;
  limits_ = {panMin / panStepsPerDegree_, panMax / panStepsPerDegree_,
             tiltMin / tiltStepsPerDegree_, tiltMax / tiltStepsPerDegree_};
  return true;
}
