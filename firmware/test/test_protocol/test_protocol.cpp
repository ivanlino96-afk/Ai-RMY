// Native unit tests for the serial protocol (docs/protocol.md) and soft-limit
// clamping. Run with `pio test -e native` from firmware/. Deliberately does
// NOT include GimbalControl.h/AccelStepper — those only target embedded
// architectures, so this suite only exercises the Arduino-free pieces
// (SerialProtocol + SoftLimits).
#include <unity.h>

#include "SerialProtocol.h"
#include "SoftLimits.h"

void test_parse_move_delta() {
  Command cmd;
  bool ok = parseCommand(
      "{\"proto\":1,\"cmd\":\"move_delta\",\"pan\":-1.5,\"tilt\":0.5,\"seq\":7}",
      cmd);

  TEST_ASSERT_TRUE(ok);
  TEST_ASSERT_TRUE(cmd.valid);
  TEST_ASSERT_EQUAL(static_cast<int>(CommandType::MoveDelta), static_cast<int>(cmd.type));
  TEST_ASSERT_EQUAL_FLOAT(-1.5f, cmd.pan);
  TEST_ASSERT_EQUAL_FLOAT(0.5f, cmd.tilt);
  TEST_ASSERT_EQUAL(7, cmd.seq);
}

void test_parse_rejects_wrong_proto_version() {
  Command cmd;
  bool ok = parseCommand("{\"proto\":2,\"cmd\":\"stop\"}", cmd);

  TEST_ASSERT_FALSE(ok);
  TEST_ASSERT_FALSE(cmd.valid);
}

void test_parse_rejects_unknown_command() {
  Command cmd;
  bool ok = parseCommand("{\"proto\":1,\"cmd\":\"dance\"}", cmd);

  TEST_ASSERT_FALSE(ok);
}

void test_parse_rejects_malformed_json() {
  Command cmd;
  bool ok = parseCommand("{not json", cmd);

  TEST_ASSERT_FALSE(ok);
}

void test_parse_stop_and_ping_have_no_payload() {
  Command stopCmd;
  TEST_ASSERT_TRUE(parseCommand("{\"proto\":1,\"cmd\":\"stop\",\"seq\":3}", stopCmd));
  TEST_ASSERT_EQUAL(static_cast<int>(CommandType::Stop), static_cast<int>(stopCmd.type));

  Command pingCmd;
  TEST_ASSERT_TRUE(parseCommand("{\"proto\":1,\"cmd\":\"ping\"}", pingCmd));
  TEST_ASSERT_EQUAL(static_cast<int>(CommandType::Ping), static_cast<int>(pingCmd.type));
}

void test_serialize_telemetry_roundtrip() {
  std::string line = serializeTelemetry(true, 42, 12.5f, -3.25f, true, false);

  TEST_ASSERT_TRUE(line.find("\"proto\":1") != std::string::npos);
  TEST_ASSERT_TRUE(line.find("\"seq\":42") != std::string::npos);
  TEST_ASSERT_TRUE(line.find("\"moving\":true") != std::string::npos);
  TEST_ASSERT_TRUE(line.find("\"homed\":false") != std::string::npos);
}

void test_serialize_telemetry_includes_error_when_present() {
  std::string line = serializeTelemetry(false, 1, 0.0f, 0.0f, false, false,
                                         "out_of_range");

  TEST_ASSERT_TRUE(line.find("\"ok\":false") != std::string::npos);
  TEST_ASSERT_TRUE(line.find("\"error\":\"out_of_range\"") != std::string::npos);
}

void test_clamp_within_range_unchanged() {
  TEST_ASSERT_EQUAL_FLOAT(10.0f, clampDeg(10.0f, -45.0f, 45.0f));
}

void test_clamp_above_max_is_clamped() {
  TEST_ASSERT_EQUAL_FLOAT(45.0f, clampDeg(90.0f, -45.0f, 45.0f));
}

void test_clamp_below_min_is_clamped() {
  TEST_ASSERT_EQUAL_FLOAT(-45.0f, clampDeg(-90.0f, -45.0f, 45.0f));
}

int main(int argc, char **argv) {
  UNITY_BEGIN();
  RUN_TEST(test_parse_move_delta);
  RUN_TEST(test_parse_rejects_wrong_proto_version);
  RUN_TEST(test_parse_rejects_unknown_command);
  RUN_TEST(test_parse_rejects_malformed_json);
  RUN_TEST(test_parse_stop_and_ping_have_no_payload);
  RUN_TEST(test_serialize_telemetry_roundtrip);
  RUN_TEST(test_serialize_telemetry_includes_error_when_present);
  RUN_TEST(test_clamp_within_range_unchanged);
  RUN_TEST(test_clamp_above_max_is_clamped);
  RUN_TEST(test_clamp_below_min_is_clamped);
  return UNITY_END();
}
