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

    def test_update_ticket_description(self):
        ticket = self.tm.create_ticket("REQ-DESC", "Chamado Descrição", "Descrição Original")
        ticket_id = ticket["id"]
        
        ok = self.tm.update_ticket_description(ticket_id, "Nova Descrição Atualizada")
        self.assertTrue(ok)
        active = self.tm.get_active_ticket()
        self.assertEqual(active["description"], "Nova Descrição Atualizada")

        # Testar via update_ticket_details
        self.tm.update_ticket_details(ticket_id, description="Descrição Final", name="Chamado Renomeado")
        active = self.tm.get_active_ticket()
        self.assertEqual(active["description"], "Descrição Final")
        self.assertEqual(active["name"], "Chamado Renomeado")

    def test_update_evidence_description(self):
        ticket = self.tm.create_ticket("REQ-EVDESC", "Chamado Evidências")
        img = Image.new("RGB", (60, 60), color="red")
        ev1 = self.tm.save_evidence(img, {"window_title": "App 1", "process_name": "app1.exe"}, "Desc 1")
        ev2 = self.tm.save_evidence(img, {"window_title": "App 2", "process_name": "app2.exe"}, "Desc 2")

        ok = self.tm.update_evidence_description(ticket["id"], 2, "Descrição 2 Modificada")
        self.assertTrue(ok)
        active = self.tm.get_active_ticket()
        self.assertEqual(active["evidences"][1]["description"], "Descrição 2 Modificada")
        self.assertEqual(active["evidences"][0]["description"], "Desc 1")

    def test_delete_evidence_and_reindex(self):
        ticket = self.tm.create_ticket("REQ-DEL", "Chamado Deleção")
        folder = Path(ticket["folder_path"])
        img = Image.new("RGB", (40, 40), color="yellow")
        ev1 = self.tm.save_evidence(img, {"window_title": "W1"}, "Primeira")
        ev2 = self.tm.save_evidence(img, {"window_title": "W2"}, "Segunda")
        ev3 = self.tm.save_evidence(img, {"window_title": "W3"}, "Terceira")

        f2 = folder / ev2["relative_path"]
        self.assertTrue(f2.exists())

        # Apaga a evidência #2
        ok = self.tm.delete_evidence(ticket["id"], 2, remove_file=True)
        self.assertTrue(ok)
        self.assertFalse(f2.exists(), "O arquivo físico da evidência apagada deve ser excluído")

        active = self.tm.get_active_ticket()
        self.assertEqual(len(active["evidences"]), 2)
        # Verifica se foram re-indexadas de 1 a N
        self.assertEqual(active["evidences"][0]["index"], 1)
        self.assertEqual(active["evidences"][0]["description"], "Primeira")
        self.assertEqual(active["evidences"][1]["index"], 2)
        self.assertEqual(active["evidences"][1]["description"], "Terceira")

    def test_reorder_evidence_up_and_down(self):
        ticket = self.tm.create_ticket("REQ-ORDER", "Chamado Reordenação")
        img = Image.new("RGB", (40, 40), color="magenta")
        self.tm.save_evidence(img, {"process_name": "p1.exe"}, "Item A")
        self.tm.save_evidence(img, {"process_name": "p2.exe"}, "Item B")
        self.tm.save_evidence(img, {"process_name": "p3.exe"}, "Item C")

        # 1. Mover item 1 para cima (não deve alterar nada, já é o primeiro)
        self.assertFalse(self.tm.move_evidence_up(ticket["id"], 1))

        # 2. Mover item 3 para cima -> deve trocar com item 2
        ok = self.tm.move_evidence_up(ticket["id"], 3)
        self.assertTrue(ok)
        active = self.tm.get_active_ticket()
        self.assertEqual([e["description"] for e in active["evidences"]], ["Item A", "Item C", "Item B"])
        self.assertEqual([e["index"] for e in active["evidences"]], [1, 2, 3])

        # 3. Mover item 1 para baixo -> deve trocar com item 2 (que agora é Item C)
        ok = self.tm.move_evidence_down(ticket["id"], 1)
        self.assertTrue(ok)
        active = self.tm.get_active_ticket()
        self.assertEqual([e["description"] for e in active["evidences"]], ["Item C", "Item A", "Item B"])
        self.assertEqual([e["index"] for e in active["evidences"]], [1, 2, 3])

        # 4. Mover último para baixo (não deve alterar)
        self.assertFalse(self.tm.move_evidence_down(ticket["id"], 3))

    def test_replace_evidence(self):
        ticket = self.tm.create_ticket("REQ-REPL", "Chamado Substituição")
        folder = Path(ticket["folder_path"])
        old_img = Image.new("RGB", (50, 50), color="black")
        ev = self.tm.save_evidence(old_img, {"process_name": "calc.exe"}, "Calculadora aberta")
        old_file = folder / ev["relative_path"]
        self.assertTrue(old_file.exists())

        # Substitui a evidência #1 por uma nova imagem verde (80x80)
        new_img = Image.new("RGB", (80, 80), color="green")
        replaced_ev = self.tm.replace_evidence(ticket["id"], 1, new_img)
        self.assertIsNotNone(replaced_ev)
        self.assertFalse(old_file.exists(), "Arquivo antigo deve ter sido removido")

        new_file = folder / replaced_ev["relative_path"]
        self.assertTrue(new_file.exists(), "Novo arquivo deve existir")
        self.assertEqual(replaced_ev["width"], 80)
        self.assertEqual(replaced_ev["height"], 80)
        self.assertEqual(replaced_ev["description"], "Calculadora aberta", "Descrição original deve ser mantida")

        active = self.tm.get_active_ticket()
        self.assertEqual(len(active["evidences"]), 1)
        self.assertEqual(active["evidences"][0]["width"], 80)

    def test_add_evidence_from_image(self):
        ticket = self.tm.create_ticket("REQ-ADD", "Chamado Adição Manual")
        img = Image.new("RGB", (70, 70), color="cyan")
        ev = self.tm.add_evidence_from_image(ticket["id"], img, description="Imagem adicionada")
        self.assertIsNotNone(ev)
        self.assertEqual(ev["index"], 1)
        self.assertEqual(ev["description"], "Imagem adicionada")
        self.assertEqual(ev["process_name"], "DeskEvidence")

        folder = Path(ticket["folder_path"])
        ev_file = folder / ev["relative_path"]
        self.assertTrue(ev_file.exists())

if __name__ == "__main__":
    unittest.main()

