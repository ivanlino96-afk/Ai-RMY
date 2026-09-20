#pragma once

// Pure, Arduino/hardware-free soft-limit clamping so it can be unit-tested
// natively (see firmware/test/) without pulling in AccelStepper, which only
// targets AVR/embedded architectures.
inline float clampDeg(float value, float lo, float hi) {
  if (value < lo) return lo;
  if (value > hi) return hi;
  return value;
}
