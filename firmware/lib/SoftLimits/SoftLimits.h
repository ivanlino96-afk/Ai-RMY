#pragma once
#include <math.h>

static const float kPanTransmission = 12000.0f / 360.0f;
static const float kTiltTransmission = 1500.0f / 55.0f;
inline long scaledSteps(float degrees, float scale) { return lround(degrees * scale); }

// Pure, Arduino/hardware-free soft-limit clamping so it can be unit-tested
// natively (see firmware/test/) without pulling in AccelStepper, which only
// targets AVR/embedded architectures.
inline float clampDeg(float value, float lo, float hi) {
  if (value < lo) return lo;
  if (value > hi) return hi;
  return value;
}

inline bool validStepTarget(long pan, long tilt, long panMin, long panMax, long tiltMin, long tiltMax) {
  return panMin >= -200000L && panMin <= 0 && panMax >= 0 && panMax <= 200000L && panMin < panMax &&
         tiltMin >= -200000L && tiltMin <= 0 && tiltMax >= 0 && tiltMax <= 200000L && tiltMin < tiltMax &&
         pan >= panMin && pan <= panMax && tilt >= tiltMin && tilt <= tiltMax;
}
