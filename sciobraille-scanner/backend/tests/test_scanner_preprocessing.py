import unittest

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


if __name__ == "__main__":
    unittest.main()
