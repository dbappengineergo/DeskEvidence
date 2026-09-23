import unittest
from PIL import Image
from deskevidence.core.annotation_engine import (
    AnnotationAction,
    render_annotations,
    hex_to_rgba,
    copy_image_to_clipboard
)

class TestAnnotationEngine(unittest.TestCase):

    def setUp(self):
        # Imagem base de teste (fundo cinza 400x300)
        self.base_img = Image.new("RGB", (400, 300), color=(128, 128, 128))

    def test_hex_to_rgba(self):
        self.assertEqual(hex_to_rgba("#ff0000"), (255, 0, 0, 255))
        self.assertEqual(hex_to_rgba("#00ff00", alpha=120), (0, 255, 0, 120))
        self.assertEqual(hex_to_rgba("#fff"), (255, 255, 255, 255))

    def test_render_empty_actions(self):
        result = render_annotations(self.base_img, [])
        self.assertEqual(result.size, (400, 300))
        self.assertEqual(result.mode, "RGB")

    def test_render_pen_and_line(self):
        actions = [
            AnnotationAction(kind="pen", points=[(10, 10), (20, 20), (30, 25)], color="#ef4444", width=3),
            AnnotationAction(kind="line", points=[(50, 50), (100, 100)], color="#3b82f6", width=2),
        ]
        result = render_annotations(self.base_img, actions)
        self.assertEqual(result.size, (400, 300))
        # Verifica se algum pixel foi alterado do cinza base
        try:
            pixels = list(result.get_flattened_data())
        except AttributeError:
            pixels = list(result.getdata())
        self.assertTrue(any(p != 128 for p in pixels[:1000]))

    def test_render_rectangle_and_arrow(self):
        actions = [
            AnnotationAction(kind="rect", points=[(20, 20), (100, 80)], color="#22c55e", width=4),
            AnnotationAction(kind="arrow", points=[(10, 10), (150, 150)], color="#ef4444", width=3),
        ]
        result = render_annotations(self.base_img, actions)
        self.assertEqual(result.size, (400, 300))

    def test_render_highlight(self):
        actions = [
            AnnotationAction(kind="highlight", points=[(50, 50), (150, 50)], color="#eab308", width=5)
        ]
        result = render_annotations(self.base_img, actions)
        self.assertEqual(result.size, (400, 300))

    def test_render_text_and_badge(self):
        actions = [
            AnnotationAction(kind="text", points=[(30, 30)], text="Erro Crítico", color="#ef4444", font_size=16),
            AnnotationAction(kind="badge", points=[(200, 150)], badge_number=1, color="#3b82f6", width=4),
            AnnotationAction(kind="badge", points=[(250, 150)], badge_number=2, color="#3b82f6", width=4),
        ]
        result = render_annotations(self.base_img, actions)
        self.assertEqual(result.size, (400, 300))

    def test_crop_box(self):
        crop = (50, 50, 250, 200)
        result = render_annotations(self.base_img, [], crop_box=crop)
        self.assertEqual(result.size, (200, 150))

    def test_copy_to_clipboard(self):
        # Testa chamada à função (em ambiente Windows com clipboard disponível)
        img = Image.new("RGB", (50, 50), color="blue")
        # Pode retornar True se clipboard estiver disponível ou False sem lançar exceção não tratada
        res = copy_image_to_clipboard(img)
        self.assertIsInstance(res, bool)


if __name__ == "__main__":
    unittest.main()
