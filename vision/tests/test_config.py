from vision.config import RecognitionConfig


def test_recognition_thresholds_and_memory_window():
    config = RecognitionConfig()
    assert config.match_threshold == 0.90
    assert config.enrollment_consistency_threshold == 0.90
    assert config.identity_memory_seconds == 30.0
