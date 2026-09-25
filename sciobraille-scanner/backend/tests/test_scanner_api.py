import unittest
from collections import deque
from unittest.mock import patch

import cv2
import numpy as np
from fastapi.testclient import TestClient

import scanner_api


def encoded_frame(value: int = 127, width: int = 8, height: int = 8) -> bytes:
    image = np.full((height, width, 3), value, dtype=np.uint8)
    ok, payload = cv2.imencode(".jpg", image)
    if not ok:
        raise AssertionError("Test image encoding failed")
    return payload.tobytes()


def contract_payload(text: str = "ab", stable: bool = False) -> dict:
    return {
        "ok": True,
        "text": text,
        "raw_text": text,
        "corrected_text": text,
        "stable": stable,
        "confidence": 0.8,
        "detections": len(text),
        "boxes": [],
        "detector_classes": 26,
        "supported_future_classes": scanner_api.FUTURE_CLASS_SCHEMA,
        "input_flipped_horizontal": True,
    }


class ScannerApiTest(unittest.TestCase):
    def setUp(self) -> None:
        scanner_api.client_histories.clear()
        self.client = TestClient(scanner_api.app)

    def tearDown(self) -> None:
        self.client.close()

    def test_root_and_health_contracts(self) -> None:
        root = self.client.get("/")
        health = self.client.get("/api/health")

        self.assertEqual(200, root.status_code)
        self.assertIn("Sciobraille", root.text)
        self.assertEqual(200, health.status_code)
        body = health.json()
        self.assertEqual(26, body["classes"])
        self.assertEqual(list("abcdefghijklmnopqrstuvwxyz"), [body["class_names"][str(i)] for i in range(26)])
        self.assertEqual(0.25, body["confidence"])
        self.assertEqual(0.45, body["iou"])
        self.assertEqual(0.70, body["duplicate_iou"])

    def test_scan_frame_response_contract(self) -> None:
        with patch.object(scanner_api, "_predict", return_value=contract_payload()):
            response = self.client.post(
                "/api/scan-frame",
                files={"frame": ("frame.jpg", encoded_frame(), "image/jpeg")},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "ok", "text", "raw_text", "corrected_text", "stable", "confidence",
                "detections", "boxes", "detector_classes", "supported_future_classes",
                "input_flipped_horizontal",
            },
            set(response.json()),
        )

    def test_rejects_non_image_empty_corrupt_and_oversized_uploads(self) -> None:
        wrong_type = self.client.post(
            "/api/scan-frame",
            files={"frame": ("frame.txt", b"text", "text/plain")},
        )
        empty = self.client.post(
            "/api/scan-frame",
            files={"frame": ("frame.jpg", b"", "image/jpeg")},
        )
        corrupt = self.client.post(
            "/api/scan-frame",
            files={"frame": ("frame.jpg", b"not-a-jpeg", "image/jpeg")},
        )
        with patch.object(scanner_api, "MAX_UPLOAD_BYTES", 4):
            oversized = self.client.post(
                "/api/scan-frame",
                files={"frame": ("frame.jpg", encoded_frame(), "image/jpeg")},
            )

        self.assertEqual(400, wrong_type.status_code)
        self.assertEqual(400, empty.status_code)
        self.assertEqual(400, corrupt.status_code)
        self.assertEqual(413, oversized.status_code)

    def test_rejects_excessive_decoded_dimensions(self) -> None:
        with patch.object(scanner_api, "MAX_IMAGE_PIXELS", 16):
            response = self.client.post(
                "/api/scan-frame",
                files={"frame": ("large.jpg", encoded_frame(width=5, height=5), "image/jpeg")},
            )

        self.assertEqual(413, response.status_code)

    def test_named_post_sessions_are_isolated(self) -> None:
        def fake_predict(frame, include_image=False, flip_horizontal=None, stabilization_history=None):
            del frame, include_image, flip_horizontal
            history = stabilization_history if stabilization_history is not None else deque(maxlen=5)
            text, stable = scanner_api._stabilize_text("alpha", history)
            return contract_payload(text, stable)

        with patch.object(scanner_api, "_predict", side_effect=fake_predict):
            first = self.client.post(
                "/api/scan-frame?client_id=one",
                files={"frame": ("frame.jpg", encoded_frame(), "image/jpeg")},
            ).json()
            first_again = self.client.post(
                "/api/scan-frame?client_id=one",
                files={"frame": ("frame.jpg", encoded_frame(), "image/jpeg")},
            ).json()
            second = self.client.post(
                "/api/scan-frame?client_id=two",
                files={"frame": ("frame.jpg", encoded_frame(), "image/jpeg")},
            ).json()

        self.assertFalse(first["stable"])
        self.assertTrue(first_again["stable"])
        self.assertFalse(second["stable"])

    def test_websocket_history_is_per_connection_and_resets_on_disconnect(self) -> None:
        def fake_predict(frame, include_image=False, flip_horizontal=None, stabilization_history=None):
            del include_image, flip_horizontal
            text_value = "alpha" if int(frame.mean()) < 150 else "beta"
            text, stable = scanner_api._stabilize_text(text_value, stabilization_history)
            return contract_payload(text, stable)

        with patch.object(scanner_api, "_predict", side_effect=fake_predict):
            with self.client.websocket_connect("/ws/scan") as first:
                first.send_bytes(encoded_frame(80))
                self.assertFalse(first.receive_json()["stable"])
                first.send_bytes(encoded_frame(80))
                self.assertTrue(first.receive_json()["stable"])
                with self.client.websocket_connect("/ws/scan") as second:
                    second.send_bytes(encoded_frame(220))
                    self.assertFalse(second.receive_json()["stable"])
            with self.client.websocket_connect("/ws/scan") as reconnected:
                reconnected.send_bytes(encoded_frame(80))
                self.assertFalse(reconnected.receive_json()["stable"])

    def test_websocket_rejects_corrupt_image_cleanly(self) -> None:
        with self.client.websocket_connect("/ws/scan") as socket:
            socket.send_bytes(b"not-an-image")
            payload = socket.receive_json()

        self.assertEqual({"ok": False, "error": "Could not decode image frame"}, payload)

    def test_websocket_forwards_flip_override(self) -> None:
        observed = []

        def fake_predict(frame, include_image=False, flip_horizontal=None, stabilization_history=None):
            del frame, include_image, stabilization_history
            observed.append(flip_horizontal)
            return contract_payload()

        with patch.object(scanner_api, "_predict", side_effect=fake_predict):
            with self.client.websocket_connect("/ws/scan?flip_horizontal=false") as socket:
                socket.send_bytes(encoded_frame())
                self.assertTrue(socket.receive_json()["ok"])

        self.assertEqual([False], observed)


if __name__ == "__main__":
    unittest.main()
