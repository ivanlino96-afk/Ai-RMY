#pragma once

#include <string>

// Implements docs/protocol.md. This is the ONLY place that should know the
// wire format — main.cpp dispatches on CommandType, it never touches JSON.
//
// Deliberately Arduino-free (plain std::string, no Arduino.h) so it compiles
// and is unit-testable on the host (`pio test -e native`), independent of the
// ESP32 toolchain. main.cpp converts to/from Arduino String at the call site.
static const int kProtocolVersion = 1;

enum class CommandType { MoveDelta, Goto, Stop, Home, Ping, Unknown };

struct Command {
  CommandType type = CommandType::Unknown;
  float pan = 0.0f;   // move_delta: delta degrees. goto: absolute degrees.
  float tilt = 0.0f;
  long seq = 0;
  bool valid = false;
};

// Parses one NDJSON line (without trailing newline) into `out`.
// Returns false (and out.valid == false) if the line is malformed, has an
// unrecognized `proto`, or an unrecognized `cmd`.
bool parseCommand(const std::string &line, Command &out);

// Builds one NDJSON telemetry/ack line (without trailing newline).
std::string serializeTelemetry(bool ok, long seq, float panDeg, float tiltDeg,
                                bool moving, bool homed,
                                const char *error = nullptr);
