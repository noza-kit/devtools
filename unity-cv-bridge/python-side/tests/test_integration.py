import json
import threading
import time

import zmq

from uzbridge import protocol
from uzbridge.config import ServerConfig
from uzbridge.ops import contour_detect
from uzbridge.pipeline import Pipeline
from uzbridge.server import BridgeServer


def test_frame_in_result_out_roundtrip(sample_jpeg):
    """Publish one frame straight over a socket (standing in for Unity /
    MockSender) and confirm a REQ client gets back a processed result."""
    config = ServerConfig(bind_host="127.0.0.1", sub_port=0, rep_port=0)
    pipeline = Pipeline().add_step(contour_detect, name="contours")
    server = BridgeServer(config, pipeline)

    sub_address = server.sub_socket.getsockopt(zmq.LAST_ENDPOINT).decode()
    rep_address = server.rep_socket.getsockopt(zmq.LAST_ENDPOINT).decode()

    thread = threading.Thread(target=server.run_forever, daemon=True)
    thread.start()

    context = zmq.Context()
    pub = context.socket(zmq.PUB)
    pub.connect(sub_address)
    time.sleep(0.3)  # let the PUB connection + subscription settle

    req = context.socket(zmq.REQ)
    req.setsockopt(zmq.RCVTIMEO, 2000)
    req.connect(rep_address)

    try:
        parts = protocol.encode_frame(sample_jpeg, frame_id=42, width=40, height=40)

        payload = None
        for _ in range(20):
            pub.send_multipart(parts)
            req.send(protocol.encode_request())
            try:
                reply = req.recv()
            except zmq.Again:
                # REQ is now stuck expecting a reply that will never come;
                # a fresh socket is the only way to retry.
                req.close(0)
                req = context.socket(zmq.REQ)
                req.setsockopt(zmq.RCVTIMEO, 2000)
                req.connect(rep_address)
                continue
            payload = json.loads(reply)
            if payload["status"] == "ok":
                break
            time.sleep(0.1)

        assert payload is not None
        assert payload["status"] == "ok"
        assert payload["frame_id"] == 42
        assert "contours" in payload["results"]
    finally:
        pub.close(0)
        req.close(0)
        context.term()
        server.stop()
        thread.join(timeout=3)
