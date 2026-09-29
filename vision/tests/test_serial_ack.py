from vision.serial_link.client import SerialLink
from vision.serial_link.protocol import Telemetry


def test_confirmation_matches_seq_not_periodic_telemetry():
    link = SerialLink()
    def send(line):
        link._accept_telemetry(Telemetry(True, 0, 0, 0, False, True))
        assert not link._pending_acks[7]['event'].is_set()
        link._accept_telemetry(Telemetry(True, 7, 0, 0, True, True))
        return True
    link._send = send
    assert link._send_confirmed('test', 7, timeout=0)
    assert not link._pending_acks


def test_rejected_ack_does_not_report_success():
    link = SerialLink()
    def send(line):
        link._accept_telemetry(Telemetry(False, 7, 0, 0, False, True, 'steps_rejected'))
        return True
    link._send = send
    assert not link._send_confirmed('test', 7, timeout=0)


def test_timeout_does_not_retry():
    link = SerialLink()
    calls = []
    link._send = lambda line: calls.append(line) or True
    assert not link._send_confirmed('test', 7, timeout=0)
    assert calls == ['test']
    assert not link._pending_acks


def test_connection_requires_recent_valid_telemetry(monkeypatch):
    from vision.serial_link import client
    link = SerialLink()
    link._connected = True
    assert not link.connected
    monkeypatch.setattr(client.time, 'monotonic', lambda: 10.0)
    link._accept_telemetry(Telemetry(True, 0, 0, 0, False, True))
    assert link.connected
    monkeypatch.setattr(client.time, 'monotonic', lambda: 14.1)
    assert not link.connected
