import tempfile
import unittest
from pathlib import Path
from PIL import Image
import customtkinter as ctk

from deskevidence.core.config_manager import ConfigManager
from deskevidence.core.ticket_manager import TicketManager
from deskevidence.ui.dialog_ticket import TicketDialog

class TestTicketDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Cria uma janela raiz oculta para os testes de CustomTkinter
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.temp_config_dir = tempfile.TemporaryDirectory()
        self.temp_storage_dir = tempfile.TemporaryDirectory()

        self.cfg = ConfigManager(config_dir=Path(self.temp_config_dir.name))
        self.cfg.set("storage_folder", self.temp_storage_dir.name)
        self.tm = TicketManager(self.cfg)

    def tearDown(self):
        self.temp_config_dir.cleanup()
        self.temp_storage_dir.cleanup()

    def test_dialog_manage_view_and_conclusion(self):
        # 1. Cria um chamado com 2 evidências
        ticket = self.tm.create_ticket("INC-UI", "Chamado UI Test", "Descrição do Chamado")
        img = Image.new("RGB", (60, 60), color="blue")
        self.tm.save_evidence(img, {"process_name": "app1.exe"}, "Desc Evidencia 1")
        self.tm.save_evidence(img, {"process_name": "app2.exe"}, "Desc Evidencia 2")

        dialog = TicketDialog(self.root, self.tm, mode="manage")
        self.root.update()

        # Verifica campo de conclusão carregado
        self.assertTrue(hasattr(dialog, "txt_conclusion"))

        # Altera a conclusão do chamado
        dialog.txt_conclusion.delete("1.0", "end")
        dialog.txt_conclusion.insert("1.0", "Conclusão Modificada na UI")

        # Salva a conclusão
        saved = dialog._save_current_conclusion()
        self.assertEqual(saved, "Conclusão Modificada na UI")

        active = self.tm.get_active_ticket()
        self.assertEqual(active["conclusion"], "Conclusão Modificada na UI")

        # Verifica que alternar para 'switch' e voltar para 'manage' não duplica widgets
        initial_child_count = len(dialog.winfo_children())
        dialog._set_mode("switch")
        self.root.update()
        dialog._set_mode("manage")
        self.root.update()
        self.assertEqual(len(dialog.winfo_children()), initial_child_count)

        dialog.destroy()

    def test_dialog_create_mode(self):
        dialog = TicketDialog(self.root, self.tm, mode="create")
        self.root.update()

        self.assertTrue(hasattr(dialog, "entry_number"))
        self.assertTrue(hasattr(dialog, "entry_name"))
        self.assertTrue(hasattr(dialog, "entry_desc"))

        dialog.entry_number.insert(0, "INC-777")
        dialog.entry_name.insert(0, "Teste Criacao")
        dialog.entry_desc.insert("1.0", "Descricao Teste")

        dialog._do_create_ticket()
        self.root.update()

        active = self.tm.get_active_ticket()
        self.assertIsNotNone(active)
        self.assertEqual(active["number"], "INC-777")
        self.assertEqual(active["name"], "Teste Criacao")
        self.assertEqual(dialog.mode, "manage")

        dialog.destroy()

if __name__ == "__main__":
    unittest.main()
