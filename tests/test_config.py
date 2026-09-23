import tempfile
import unittest
from pathlib import Path
from deskevidence.core.config_manager import ConfigManager, DEFAULT_HOTKEYS

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)
        self.cfg = ConfigManager(config_dir=self.config_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_values(self):
        self.assertEqual(self.cfg.get("capture_mode"), "active_window")
        self.assertTrue(self.cfg.get("prompt_quick_note"))
        self.assertTrue(self.cfg.get("generate_html_on_finish"))
        self.assertEqual(self.cfg.get_hotkey("capture"), DEFAULT_HOTKEYS["capture"])

    def test_update_and_save(self):
        self.cfg.set("capture_mode", "fullscreen")
        self.cfg.set_hotkey("capture", "ctrl+alt+s")
        
        # Recarrega de uma nova instância apontando para o mesmo diretório
        new_cfg = ConfigManager(config_dir=self.config_dir)
        self.assertEqual(new_cfg.get("capture_mode"), "fullscreen")
        self.assertEqual(new_cfg.get_hotkey("capture"), "ctrl+alt+s")

if __name__ == "__main__":
    unittest.main()
