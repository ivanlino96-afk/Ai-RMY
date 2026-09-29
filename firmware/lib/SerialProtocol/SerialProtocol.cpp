#include "SerialProtocol.h"

#include <ArduinoJson.h>
#include <string.h>

bool parseCommand(const ProtocolString &line, Command &out) {
  out = Command{};

  #if ARDUINOJSON_VERSION_MAJOR < 7
  // AVR has only 2 KB RAM. Reserve slots + duplicated input strings,
  // not a generic oversized pool that competes with the serial buffer.
  StaticJsonDocument<JSON_OBJECT_SIZE(13) + 180> doc;
  #else
  JsonDocument doc;
  #endif
  DeserializationError err = deserializeJson(doc, line);
  if (err) return false;

  if (!doc["proto"].is<int>() || doc["proto"].as<int>() != kProtocolVersion) {
    return false;
  }

  const char *cmd = doc["cmd"] | "";
  out.seq = doc["seq"] | 0;

  if (strcmp(cmd, "move_steps") == 0) {
    if (!doc["pan_steps"].is<long>() || !doc["tilt_steps"].is<long>()) return false;
    out.panSteps = doc["pan_steps"].as<long>();
    out.tiltSteps = doc["tilt_steps"].as<long>();
    if (out.panSteps < -2000 || out.panSteps > 2000 ||
        out.tiltSteps < -2000 || out.tiltSteps > 2000 ||
        (out.panSteps == 0) == (out.tiltSteps == 0)) return false;
    out.type = CommandType::MoveSteps;
  } else if (strcmp(cmd, "move_delta") == 0) {
    out.type = CommandType::MoveDelta;
    out.pan = doc["pan"] | 0.0f;
    out.tilt = doc["tilt"] | 0.0f;
  } else if (strcmp(cmd, "goto") == 0) {
    out.type = CommandType::Goto;
    out.pan = doc["pan_deg"] | 0.0f;
    out.tilt = doc["tilt_deg"] | 0.0f;
  } else if (strcmp(cmd, "stop") == 0) {
    out.type = CommandType::Stop;
  } else if (strcmp(cmd, "home") == 0) {
    out.type = CommandType::Home;
  } else if (strcmp(cmd, "ping") == 0) {
    out.type = CommandType::Ping;
  } else {
    out.type = CommandType::Unknown;
    return false;
  }

  if (out.type == CommandType::MoveSteps || out.type == CommandType::MoveDelta ||
      out.type == CommandType::Goto) {
    if (!doc["pan_speed"].isNull() || !doc["tilt_speed"].isNull()) {
      if (!doc["pan_speed"].is<long>() || !doc["tilt_speed"].is<long>()) return false;
      out.panSpeed = doc["pan_speed"].as<long>();
      out.tiltSpeed = doc["tilt_speed"].as<long>();
      if (out.panSpeed < 1 || out.panSpeed > 4000 || out.tiltSpeed < 1 || out.tiltSpeed > 4000) return false;
    }
  }
  if (out.type == CommandType::MoveSteps || out.type == CommandType::MoveDelta || out.type == CommandType::Goto) {
    if (!doc["pan_accel"].isNull() || !doc["tilt_accel"].isNull()) {
      if (!doc["pan_accel"].is<long>() || !doc["tilt_accel"].is<long>()) return false;
      out.panAccel = doc["pan_accel"].as<long>();
      out.tiltAccel = doc["tilt_accel"].as<long>();
      if (out.panAccel < 1 || out.panAccel > 20000 || out.tiltAccel < 1 || out.tiltAccel > 20000) return false;
    }
  }
  if (out.type == CommandType::MoveSteps || out.type == CommandType::MoveDelta || out.type == CommandType::Goto) {
    const char *keys[] = {"pan_min", "pan_max", "tilt_min", "tilt_max"};
    bool hasLimits = false;
    for (auto key : keys) if (doc.containsKey(key)) hasLimits = true;
    if (hasLimits) {
      for (auto key : keys) if (!doc[key].is<long>() || doc[key].as<long>() < -200000L || doc[key].as<long>() > 200000L) return false;
      out.panMin = doc["pan_min"]; out.panMax = doc["pan_max"];
      out.tiltMin = doc["tilt_min"]; out.tiltMax = doc["tilt_max"];
      if (out.panMin > 0 || out.panMax < 0 || out.panMin >= out.panMax ||
          out.tiltMin > 0 || out.tiltMax < 0 || out.tiltMin >= out.tiltMax) return false;
    }
  }
  out.valid = true;
  return true;
}

template <typename Output>
void emitTelemetry(Output &output, bool ok, long seq, float panDeg, float tiltDeg,
                                bool moving, bool homed, const char *error, bool calibration, long panSteps, long tiltSteps) {
  #if ARDUINOJSON_VERSION_MAJOR < 7
  // Output keys and error are const strings: ArduinoJson stores pointers.
  StaticJsonDocument<JSON_OBJECT_SIZE(12) + 32> doc;
  #else
  JsonDocument doc;
  #endif
  doc["proto"] = kProtocolVersion;
  doc["ok"] = ok;
  doc["seq"] = seq;
  doc["pan_deg"] = panDeg;
  doc["tilt_deg"] = tiltDeg;
  doc["moving"] = moving;
  doc["homed"] = homed;
  doc["calibration"] = calibration;
  doc["pan_steps"] = panSteps;
  doc["tilt_steps"] = tiltSteps;
  if (error != nullptr) doc["error"] = error;

  serializeJson(doc, output);
}


ProtocolString serializeTelemetry(bool ok, long seq, float panDeg, float tiltDeg,
                                bool moving, bool homed, const char *error, bool calibration, long panSteps, long tiltSteps) {
  ProtocolString output;
  emitTelemetry(output, ok, seq, panDeg, tiltDeg, moving, homed, error, calibration, panSteps, tiltSteps);
  return output;
}

#if defined(ARDUINO_ARCH_AVR)
void writeTelemetry(Print &output, bool ok, long seq, float panDeg, float tiltDeg,
                    bool moving, bool homed, const char *error, bool calibration, long panSteps, long tiltSteps) {
  // Stream directly: retaining an input String plus an output String exceeded
  // available heap on the 2 KB Uno and silently truncated outgoing JSON.
  emitTelemetry(output, ok, seq, panDeg, tiltDeg, moving, homed, error, calibration, panSteps, tiltSteps);
  output.println();
}
#endif
