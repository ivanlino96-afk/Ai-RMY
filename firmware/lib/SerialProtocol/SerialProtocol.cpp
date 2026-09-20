#include "SerialProtocol.h"

#include <ArduinoJson.h>

bool parseCommand(const std::string &line, Command &out) {
  out = Command{};

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) return false;

  if (!doc["proto"].is<int>() || doc["proto"].as<int>() != kProtocolVersion) {
    return false;
  }

  std::string cmd = doc["cmd"] | "";
  out.seq = doc["seq"] | 0;

  if (cmd == "move_delta") {
    out.type = CommandType::MoveDelta;
    out.pan = doc["pan"] | 0.0f;
    out.tilt = doc["tilt"] | 0.0f;
  } else if (cmd == "goto") {
    out.type = CommandType::Goto;
    out.pan = doc["pan_deg"] | 0.0f;
    out.tilt = doc["tilt_deg"] | 0.0f;
  } else if (cmd == "stop") {
    out.type = CommandType::Stop;
  } else if (cmd == "home") {
    out.type = CommandType::Home;
  } else if (cmd == "ping") {
    out.type = CommandType::Ping;
  } else {
    out.type = CommandType::Unknown;
    return false;
  }

  out.valid = true;
  return true;
}

std::string serializeTelemetry(bool ok, long seq, float panDeg, float tiltDeg,
                                bool moving, bool homed, const char *error) {
  JsonDocument doc;
  doc["proto"] = kProtocolVersion;
  doc["ok"] = ok;
  doc["seq"] = seq;
  doc["pan_deg"] = panDeg;
  doc["tilt_deg"] = tiltDeg;
  doc["moving"] = moving;
  doc["homed"] = homed;
  if (error != nullptr) doc["error"] = error;

  std::string out;
  serializeJson(doc, out);
  return out;
}
