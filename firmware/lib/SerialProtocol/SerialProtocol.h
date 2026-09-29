#pragma once

#if defined(ARDUINO_ARCH_AVR)
#include <Arduino.h>
using ProtocolString = String;
#else
#include <string>
using ProtocolString = std::string;
#endif

// Implements docs/protocol.md. This is the ONLY place that should know the
// wire format — main.cpp dispatches on CommandType, it never touches JSON.
//
// Deliberately Arduino-free (plain std::string, no Arduino.h) so it compiles
// and is unit-testable on the host (`pio test -e native`), independent of the
// target microcontroller's toolchain. main.cpp converts to/from Arduino String
// at the call site.
static const int kProtocolVersion = 1;

enum class CommandType { MoveSteps, MoveDelta, Goto, Stop, Home, Ping, Unknown };

struct Command {
  CommandType type = CommandType::Unknown;
  float pan = 0.0f;   // move_delta: delta degrees. goto: absolute degrees.
  float tilt = 0.0f;
  long panMin = 0, panMax = 12000, tiltMin = -1500, tiltMax = 1500;
  long seq = 0;
  long panAccel = 0;
  long tiltAccel = 0;
  long panSpeed = 0;
  long tiltSpeed = 0;
  long panSteps = 0;
  long tiltSteps = 0;
  bool valid = false;
};

// Parses one NDJSON line (without trailing newline) into `out`.
// Returns false (and out.valid == false) if the line is malformed, has an
// unrecognized `proto`, or an unrecognized `cmd`.
bool parseCommand(const ProtocolString &line, Command &out);

// Builds one NDJSON telemetry/ack line (without trailing newline).
ProtocolString serializeTelemetry(bool ok, long seq, float panDeg, float tiltDeg,
                                bool moving, bool homed,
                                const char *error = nullptr, bool calibration = false,
                                long panSteps = 0, long tiltSteps = 0);

#if defined(ARDUINO_ARCH_AVR)
void writeTelemetry(Print &output, bool ok, long seq, float panDeg, float tiltDeg,
                    bool moving, bool homed, const char *error, bool calibration, long panSteps, long tiltSteps);
#endif
