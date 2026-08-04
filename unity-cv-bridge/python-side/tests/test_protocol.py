import pytest

from uzbridge import protocol


def test_encode_decode_frame_roundtrip(sample_jpeg):
    parts = protocol.encode_frame(sample_jpeg, frame_id=7, width=40, height=40, timestamp=123.5)
    assert parts[0] == protocol.TOPIC_FRAME

    msg = protocol.decode_frame(parts)
    assert msg.frame_id == 7
    assert msg.width == 40
    assert msg.height == 40
    assert msg.timestamp == 123.5
    assert msg.jpeg_bytes == sample_jpeg


def test_encode_frame_defaults_timestamp(sample_jpeg):
    parts = protocol.encode_frame(sample_jpeg, frame_id=1, width=10, height=10)
    msg = protocol.decode_frame(parts)
    assert msg.timestamp > 0


def test_decode_frame_wrong_part_count_raises():
    with pytest.raises(ValueError):
        protocol.decode_frame([b"only", b"two"])


def test_encode_decode_request_roundtrip():
    data = protocol.encode_request(frame_id=3)
    assert protocol.decode_request(data) == {"frame_id": 3}


def test_decode_request_handles_empty_and_garbage():
    assert protocol.decode_request(b"") == {}
    assert protocol.decode_request(b"not json") == {}
