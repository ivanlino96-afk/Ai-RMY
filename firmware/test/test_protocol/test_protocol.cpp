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

void test_step_calibration_validation() {
  Command cmd;
  TEST_ASSERT_TRUE(parseCommand("{\"proto\":1,\"cmd\":\"move_steps\",\"pan_steps\":2000,\"tilt_steps\":0}", cmd));
  TEST_ASSERT_EQUAL(2000, cmd.panSteps);
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"move_steps\",\"pan_steps\":2001,\"tilt_steps\":0}", cmd));
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"move_steps\",\"pan_steps\":1,\"tilt_steps\":1}", cmd));
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"move_steps\",\"pan_steps\":1.5,\"tilt_steps\":0}", cmd));
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"move_steps\",\"pan_steps\":0,\"tilt_steps\":0}", cmd));
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"move_steps\",\"pan_steps\":1}", cmd));
  TEST_ASSERT_TRUE(parseCommand("{\"proto\":1,\"cmd\":\"move_steps\",\"pan_steps\":0,\"tilt_steps\":-2000}", cmd));
  TEST_ASSERT_EQUAL(-2000, cmd.tiltSteps);
}

void test_step_counters_telemetry() {
  auto line = serializeTelemetry(true, 1, 0, 0, false, true, nullptr, true, 1234, -4321);
  TEST_ASSERT_TRUE(line.find("\"calibration\":true") != std::string::npos);
  TEST_ASSERT_TRUE(line.find("\"pan_steps\":1234") != std::string::npos);
  TEST_ASSERT_TRUE(line.find("\"tilt_steps\":-4321") != std::string::npos);
}

void test_motion_speed_validation() {
  Command cmd;
  TEST_ASSERT_TRUE(parseCommand("{\"proto\":1,\"cmd\":\"move_steps\",\"pan_steps\":20,\"tilt_steps\":0,\"pan_speed\":160,\"tilt_speed\":400}", cmd));
  TEST_ASSERT_EQUAL(160, cmd.panSpeed);
  TEST_ASSERT_EQUAL(400, cmd.tiltSpeed);
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"goto\",\"pan_speed\":4001,\"tilt_speed\":40}", cmd));
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"goto\",\"pan_speed\":0,\"tilt_speed\":40}", cmd));
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"goto\",\"pan_speed\":10.5,\"tilt_speed\":40}", cmd));
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"goto\",\"pan_speed\":80}", cmd));
  TEST_ASSERT_TRUE(parseCommand("{\"proto\":1,\"cmd\":\"goto\"}", cmd));
  TEST_ASSERT_EQUAL(0, cmd.panSpeed);
}

void test_acceleration_validation() {
  Command cmd;
  TEST_ASSERT_TRUE(parseCommand("{\"proto\":1,\"cmd\":\"move_steps\",\"pan_steps\":2000,\"tilt_steps\":0,\"seq\":12345,\"pan_speed\":4000,\"tilt_speed\":1000,\"pan_accel\":20000,\"tilt_accel\":1000}", cmd));
  TEST_ASSERT_EQUAL(20000, cmd.panAccel);
  TEST_ASSERT_EQUAL(1000, cmd.tiltAccel);
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"goto\",\"pan_accel\":0,\"tilt_accel\":40}", cmd));
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"goto\",\"pan_accel\":20001,\"tilt_accel\":40}", cmd));
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"goto\",\"pan_accel\":10.5,\"tilt_accel\":40}", cmd));
  TEST_ASSERT_FALSE(parseCommand("{\"proto\":1,\"cmd\":\"goto\",\"pan_accel\":80}", cmd));
}

void test_step_limits() {
  TEST_ASSERT_TRUE(validStepTarget(12000, -1500, 0, 12000, -1500, 1500));
  TEST_ASSERT_TRUE(validStepTarget(0, 1500, 0, 12000, -1500, 1500));
  TEST_ASSERT_FALSE(validStepTarget(12001, 0, 0, 12000, -1500, 1500));
  TEST_ASSERT_FALSE(validStepTarget(-1, 0, 0, 12000, -1500, 1500));
  TEST_ASSERT_FALSE(validStepTarget(0, -1501, 0, 12000, -1500, 1500));
  TEST_ASSERT_FALSE(validStepTarget(0, 1501, 0, 12000, -1500, 1500));
  Command cmd;
  TEST_ASSERT_TRUE(parseCommand(R"({"proto":1,"cmd":"move_steps","pan_steps":20,"tilt_steps":0,"pan_min":0,"pan_max":12000,"tilt_min":-1500,"tilt_max":1500,"pan_speed":4000,"tilt_speed":4000,"pan_accel":20000,"tilt_accel":20000,"seq":12345})", cmd));
  TEST_ASSERT_EQUAL(12000, cmd.panMax);
  TEST_ASSERT_FALSE(parseCommand(R"({"proto":1,"cmd":"move_steps","pan_steps":20,"tilt_steps":0,"pan_min":0})", cmd));
}

void test_measured_transmission_and_angular_envelope() {
  TEST_ASSERT_EQUAL(12000, scaledSteps(360.0f, kPanTransmission));
  TEST_ASSERT_EQUAL(6000, scaledSteps(180.0f, kPanTransmission));
  TEST_ASSERT_EQUAL(1500, scaledSteps(55.0f, kTiltTransmission));
  TEST_ASSERT_EQUAL(-1500, scaledSteps(-55.0f, kTiltTransmission));
  TEST_ASSERT_EQUAL(12000, scaledSteps(clampDeg(361.0f, 0.0f, 360.0f), kPanTransmission));
  TEST_ASSERT_EQUAL(0, scaledSteps(clampDeg(-1.0f, 0.0f, 360.0f), kPanTransmission));
  Command cmd;
  TEST_ASSERT_TRUE(parseCommand(R"({"proto":1,"cmd":"move_delta","pan":-1,"tilt":1,"pan_min":0,"pan_max":10000,"tilt_min":-1000,"tilt_max":1000})", cmd));
  TEST_ASSERT_EQUAL(10000, cmd.panMax);
  TEST_ASSERT_EQUAL(-1000, cmd.tiltMin);
  TEST_ASSERT_FALSE(parseCommand(R"({"proto":1,"cmd":"goto","pan_min":0,"pan_max":10000,"tilt_min":1,"tilt_max":1000})", cmd));
}

int main(int argc, char **argv) {
  UNITY_BEGIN();
  RUN_TEST(test_measured_transmission_and_angular_envelope);
  RUN_TEST(test_step_limits);
  RUN_TEST(test_acceleration_validation);
  RUN_TEST(test_motion_speed_validation);
  RUN_TEST(test_step_calibration_validation);
  RUN_TEST(test_step_counters_telemetry);
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
