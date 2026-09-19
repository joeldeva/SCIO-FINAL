import unittest
from collections import deque

import numpy as np

import scanner_api


class ScannerPreprocessingTest(unittest.TestCase):
    def test_horizontal_flip_mirrors_columns(self) -> None:
        frame = np.array([[[1, 1, 1], [2, 2, 2], [3, 3, 3]]], dtype=np.uint8)

        flipped = scanner_api._prepare_model_frame(frame, flip_horizontal=True)

        self.assertEqual([3, 2, 1], flipped[0, :, 0].tolist())

    def test_disabled_flip_preserves_frame(self) -> None:
        frame = np.array([[[1, 1, 1], [2, 2, 2], [3, 3, 3]]], dtype=np.uint8)

        unchanged = scanner_api._prepare_model_frame(frame, flip_horizontal=False)

        self.assertTrue(np.array_equal(frame, unchanged))

    def test_dmi_acronym_is_not_spell_corrected(self) -> None:
        self.assertEqual("dmi college", scanner_api._correct_text("dmi college"))

    def test_stabilization_isolated_per_client_history(self) -> None:
        first = deque(maxlen=5)
        second = deque(maxlen=5)

        self.assertEqual(("alpha", False), scanner_api._stabilize_text("alpha", first))
        self.assertEqual(("alpha", True), scanner_api._stabilize_text("alpha", first))
        self.assertEqual(("beta", False), scanner_api._stabilize_text("beta", second))

    def test_stabilization_resets_for_different_page(self) -> None:
        history = deque(["first page", "first page"], maxlen=5)

        text, stable = scanner_api._stabilize_text("unrelated content", history)

        self.assertEqual("unrelated content", text)
        self.assertFalse(stable)
        self.assertEqual(["unrelated content"], list(history))

    def test_adaptive_spacing_ignores_moderate_intra_word_variance(self) -> None:
        line = [
            {"x_center": 10.0, "width": 8.0, "label": "a"},
            {"x_center": 20.0, "width": 8.0, "label": "b"},
            {"x_center": 32.0, "width": 8.0, "label": "c"},
            {"x_center": 60.0, "width": 8.0, "label": "d"},
        ]

        self.assertEqual(["a", "b", "c", "space", "d"], scanner_api._insert_adaptive_spaces(line))

    def test_reading_order_handles_vertical_variance_and_multiple_lines(self) -> None:
        detections = [
            {"x_center": 30.0, "y_center": 12.0, "width": 8.0, "height": 16.0, "label": "b"},
            {"x_center": 10.0, "y_center": 10.0, "width": 8.0, "height": 16.0, "label": "a"},
            {"x_center": 30.0, "y_center": 52.0, "width": 8.0, "height": 16.0, "label": "d"},
            {"x_center": 10.0, "y_center": 50.0, "width": 8.0, "height": 16.0, "label": "c"},
        ]

        self.assertEqual("ab\ncd", scanner_api._reading_order_adaptive(detections))

    def test_reading_order_empty_detections_is_empty(self) -> None:
        self.assertEqual("", scanner_api._reading_order_adaptive([]))

    def test_duplicate_boxes_keep_highest_confidence_across_classes(self) -> None:
        detections = [
            {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 10.0, "label": "a", "confidence": 0.90},
            {"x1": 0.2, "y1": 0.2, "x2": 10.2, "y2": 10.2, "label": "b", "confidence": 0.80},
            {"x1": 20.0, "y1": 0.0, "x2": 30.0, "y2": 10.0, "label": "c", "confidence": 0.70},
        ]

        kept = scanner_api._deduplicate_detections(detections)

        self.assertEqual(["a", "c"], [item["label"] for item in kept])

    def test_stabilization_selects_repeated_live_reading(self) -> None:
        history = deque(maxlen=5)
        sequence = ["hello", "heilo", "hello", "hello", "hello"]

        results = [scanner_api._stabilize_text(value, history) for value in sequence]

        self.assertEqual(("hello", True), results[-1])

    def test_stabilization_replaces_stale_scene(self) -> None:
        history = deque(maxlen=5)
        for value in ["hello", "hello", "hello"]:
            scanner_api._stabilize_text(value, history)

        first_world = scanner_api._stabilize_text("world", history)
        second_world = scanner_api._stabilize_text("world", history)

        self.assertEqual(("world", False), first_world)
        self.assertEqual(("world", True), second_world)

    def test_unnamed_post_history_is_stateless(self) -> None:
        first = scanner_api._history_for_client(None)
        second = scanner_api._history_for_client(None)

        self.assertIsNot(first, second)

    def test_model_class_order_is_canonical_alphabet(self) -> None:
        ordered = [scanner_api.names[index] for index in range(26)]

        self.assertEqual(list("abcdefghijklmnopqrstuvwxyz"), ordered)

    def test_production_threshold_contract(self) -> None:
        self.assertEqual(0.50, scanner_api.CONFIDENCE)
        self.assertEqual(0.50, scanner_api.IOU)
        self.assertEqual(0.70, scanner_api.DUPLICATE_IOU)
        self.assertEqual(640, scanner_api.IMGSZ)
        self.assertTrue(scanner_api.AUGMENT_INFERENCE)
        self.assertGreaterEqual(scanner_api.MAX_UPLOAD_BYTES, 1024 * 1024)
        self.assertGreaterEqual(scanner_api.MAX_IMAGE_PIXELS, 1_000_000)

    def test_named_client_histories_are_isolated(self) -> None:
        first = scanner_api._history_for_client("test-client-one")
        first_again = scanner_api._history_for_client("test-client-one")
        second = scanner_api._history_for_client("test-client-two")

        self.assertIs(first, first_again)
        self.assertIsNot(first, second)


if __name__ == "__main__":
    unittest.main()
