import unittest
import win32con
from deskevidence.core.hotkey_manager import parse_hotkey_string, MOD_NOREPEAT

class TestHotkeyParser(unittest.TestCase):
    def test_parse_combinations(self):
        # ctrl+shift+e
        res = parse_hotkey_string("ctrl+shift+e")
        self.assertIsNotNone(res)
        mods, vk = res
        expected_mods = MOD_NOREPEAT | win32con.MOD_CONTROL | win32con.MOD_SHIFT
        self.assertEqual(mods, expected_mods)
        self.assertEqual(vk, ord('E'))

        # ctrl+f10
        res = parse_hotkey_string("ctrl+f10")
        self.assertIsNotNone(res)
        mods, vk = res
        expected_mods = MOD_NOREPEAT | win32con.MOD_CONTROL
        self.assertEqual(mods, expected_mods)
        self.assertEqual(vk, win32con.VK_F10)

        # alt+prtscn
        res = parse_hotkey_string("alt+printscreen")
        self.assertIsNotNone(res)
        mods, vk = res
        expected_mods = MOD_NOREPEAT | win32con.MOD_ALT
        self.assertEqual(mods, expected_mods)
        self.assertEqual(vk, win32con.VK_SNAPSHOT)

    def test_invalid_string(self):
        self.assertIsNone(parse_hotkey_string(""))
        self.assertIsNone(parse_hotkey_string("ctrl+shift"))  # Falta a tecla final

if __name__ == "__main__":
    unittest.main()
