import unittest
from unittest.mock import patch
from PIL import Image
from deskevidence.core.capture_engine import CaptureEngine

class TestCaptureEngine(unittest.TestCase):
    @patch("deskevidence.core.capture_engine.ImageGrab.grab")
    def test_fullscreen_capture_mocked(self, mock_grab):
        mock_grab.return_value = Image.new("RGB", (1400, 790), color="white")
        engine = CaptureEngine(mode="fullscreen")
        res = engine.capture()
        self.assertIsNotNone(res)
        self.assertIsNotNone(res.image)
        self.assertEqual(res.image.width, 1400)
        self.assertEqual(res.image.height, 790)
        self.assertEqual(res.metadata.get("mode"), "fullscreen")

    @patch("deskevidence.core.capture_engine.ImageGrab.grab")
    def test_active_window_fallback_when_no_foreground(self, mock_grab):
        # Quando hwnd é 0 (tela bloqueada ou sem foco), faz fallback gracioso para fullscreen
        mock_grab.return_value = Image.new("RGB", (1400, 790), color="gray")
        engine = CaptureEngine(mode="active_window")
        res = engine.capture()
        self.assertIsNotNone(res)
        self.assertIsNotNone(res.image)

if __name__ == "__main__":
    unittest.main()
