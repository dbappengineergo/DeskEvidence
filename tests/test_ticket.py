import tempfile
import unittest
from pathlib import Path
from PIL import Image

from deskevidence.core.config_manager import ConfigManager
from deskevidence.core.ticket_manager import TicketManager

class TestTicketManager(unittest.TestCase):
    def setUp(self):
        self.temp_config_dir = tempfile.TemporaryDirectory()
        self.temp_storage_dir = tempfile.TemporaryDirectory()
        
        self.cfg = ConfigManager(config_dir=Path(self.temp_config_dir.name))
        self.cfg.set("storage_folder", self.temp_storage_dir.name)
        
        self.tm = TicketManager(self.cfg)

    def tearDown(self):
        self.temp_config_dir.cleanup()
        self.temp_storage_dir.cleanup()

    def test_create_and_active_ticket(self):
        ticket = self.tm.create_ticket("INC123", "Homologação Teste", "Descrição de teste")
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket["number"], "INC123")
        self.assertEqual(ticket["status"], "active")

        active = self.tm.get_active_ticket()
        self.assertEqual(active["id"], ticket["id"])

    def test_save_evidence(self):
        self.tm.create_ticket("CH001", "Verificação")
        
        img = Image.new("RGB", (200, 200), color="blue")
        metadata = {
            "window_title": "Janela Teste",
            "process_name": "notepad.exe",
            "mode": "active_window"
        }
        
        ev = self.tm.save_evidence(img, metadata, description="Evidência teste de salvar")
        self.assertIsNotNone(ev)
        self.assertEqual(ev["index"], 1)
        self.assertEqual(ev["process_name"], "notepad.exe")

        active = self.tm.get_active_ticket()
        self.assertEqual(len(active["evidences"]), 1)

    def test_finish_ticket_generates_html(self):
        self.tm.create_ticket("REQ999", "Fechamento")
        img = Image.new("RGB", (100, 100), color="green")
        self.tm.save_evidence(img, {"window_title": "App", "process_name": "app.exe"}, "Nota 1")

        completed, report_path = self.tm.finish_active_ticket()
        self.assertEqual(completed["status"], "completed")
        self.assertIsNone(self.tm.get_active_ticket())
        
        self.assertIsNotNone(report_path)
        html_file = Path(report_path)
        self.assertTrue(html_file.exists())
        
        html_text = html_file.read_text(encoding="utf-8")
        self.assertTrue(html_text.startswith("<!DOCTYPE html>"))
        # Verifica a presença dos botões de PDF e Word no HTML
        self.assertIn("btn-pdf", html_text)
        self.assertIn("window.print()", html_text)
        self.assertIn("btn-word", html_text)
        self.assertIn("exportToWord()", html_text)

        # Verifica a geração do arquivo .doc direto na pasta
        doc_file = html_file.parent / "relatorio_evidencias.doc"
        self.assertTrue(doc_file.exists())
        doc_text = doc_file.read_text(encoding="utf-8")
        self.assertIn("urn:schemas-microsoft-com:office:word", doc_text)

    def test_report_builder_empty_evidences(self):
        from deskevidence.core.report_builder import generate_html_report, generate_word_report
        ticket_data = {
            "number": "T001",
            "name": "Chamado Vazio",
            "description": "Nenhuma evidencia ainda",
            "evidences": []
        }
        out_html = Path(self.temp_storage_dir.name) / "test_empty.html"
        out_doc = Path(self.temp_storage_dir.name) / "test_empty.doc"
        
        generate_html_report(ticket_data, out_html)
        generate_word_report(ticket_data, out_doc)
        
        self.assertTrue(out_html.exists())
        self.assertTrue(out_doc.exists())
        self.assertIn("Nenhuma evidência", out_html.read_text(encoding="utf-8"))
        self.assertIn("Nenhuma evidência", out_doc.read_text(encoding="utf-8"))

    def test_reactivate_completed_ticket(self):
        # 1. Cria e finaliza o chamado
        ticket = self.tm.create_ticket("REQ-REACTIVE", "Chamado para Reativação")
        ticket_id = ticket["id"]
        completed, report_path = self.tm.finish_active_ticket()
        self.assertIsNone(self.tm.get_active_ticket())
        
        # 2. Reativa o chamado via set_active_ticket
        reactivated = self.tm.set_active_ticket(ticket_id)
        self.assertIsNotNone(reactivated)
        self.assertEqual(reactivated["status"], "active")
        self.assertIsNone(reactivated["closed_at"])
        
        # 3. get_active_ticket deve retornar o chamado ativo
        active = self.tm.get_active_ticket()
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], ticket_id)
        self.assertEqual(active["status"], "active")

    def test_export_reports_method(self):
        ticket = self.tm.create_ticket("REQ-EXPORT", "Chamado Export")
        img = Image.new("RGB", (50, 50), color="blue")
        self.tm.save_evidence(img, {"window_title": "App Test", "process_name": "test.exe"}, "Teste de export")
        
        html_p, doc_p = self.tm.export_reports()
        self.assertTrue(Path(html_p).exists())
        self.assertTrue(Path(doc_p).exists())
        self.assertIn("REQ-EXPORT", Path(html_p).read_text(encoding="utf-8"))
        self.assertIn("REQ-EXPORT", Path(doc_p).read_text(encoding="utf-8"))

    def test_ticket_conclusion(self):
        ticket = self.tm.create_ticket("REQ-CONCL", "Chamado com Conclusão")
        ticket_id = ticket["id"]
        
        # 1. Atualizar conclusão via método
        ok = self.tm.update_ticket_conclusion(ticket_id, "Ambiente testado e homologado.")
        self.assertTrue(ok)
        active = self.tm.get_active_ticket()
        self.assertEqual(active["conclusion"], "Ambiente testado e homologado.")

        # 2. Finalizar com conclusão personalizada
        conclusion_text = "Chamado resolvido com sucesso após correção no banco de dados."
        completed, report_path = self.tm.finish_active_ticket(conclusion=conclusion_text)
        self.assertEqual(completed["conclusion"], conclusion_text)

        html_content = Path(report_path).read_text(encoding="utf-8")
        self.assertIn("conclusion-card", html_content)
        self.assertIn("Conclusão / Parecer Técnico", html_content)
        self.assertIn("Chamado resolvido com sucesso", html_content)

        doc_path = Path(report_path).parent / "relatorio_evidencias.doc"
        self.assertTrue(doc_path.exists())
        doc_content = doc_path.read_text(encoding="utf-8")
        self.assertIn("Chamado resolvido com sucesso", doc_content)

if __name__ == "__main__":
    unittest.main()
