import tempfile
import unittest
from pathlib import Path
from PIL import Image

from deskevidence.core.config_manager import ConfigManager
from deskevidence.core.ticket_manager import TicketManager

class TestEndToEndEvidenceWorkflow(unittest.TestCase):
    def test_full_evidence_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp_cfg, tempfile.TemporaryDirectory() as tmp_storage:
            cfg = ConfigManager(config_dir=Path(tmp_cfg))
            cfg.set("storage_folder", tmp_storage)
            tm = TicketManager(cfg)

            # 1. Cria chamado
            ticket = tm.create_ticket("INC-9999", "Fluxo Completo de Evidências", "Descrição Inicial")
            tid = ticket["id"]

            # 2. Adiciona 3 evidências
            img_red = Image.new("RGB", (100, 100), color="red")
            img_green = Image.new("RGB", (100, 100), color="green")
            img_blue = Image.new("RGB", (100, 100), color="blue")

            tm.save_evidence(img_red, {"process_name": "red.exe"}, "Evidência Vermelha")
            tm.save_evidence(img_green, {"process_name": "green.exe"}, "Evidência Verde")
            tm.save_evidence(img_blue, {"process_name": "blue.exe"}, "Evidência Azul")

            # 3. Mover evidência 3 para cima (troca Azul com Verde)
            tm.move_evidence_up(tid, 3)
            active = tm.get_active_ticket()
            order = [e["description"] for e in active["evidences"]]
            self.assertEqual(order, ["Evidência Vermelha", "Evidência Azul", "Evidência Verde"])

            # 4. Apagar evidência 1 (Vermelha)
            tm.delete_evidence(tid, 1)
            active = tm.get_active_ticket()
            order = [e["description"] for e in active["evidences"]]
            indices = [e["index"] for e in active["evidences"]]
            self.assertEqual(order, ["Evidência Azul", "Evidência Verde"])
            self.assertEqual(indices, [1, 2])

            # 5. Substituir evidência 1 (Azul) por imagem Amarela
            img_yellow = Image.new("RGB", (120, 120), color="yellow")
            tm.replace_evidence(tid, 1, img_yellow, "Evidência Amarela Substituta")
            active = tm.get_active_ticket()
            self.assertEqual(active["evidences"][0]["description"], "Evidência Amarela Substituta")
            self.assertEqual(active["evidences"][0]["width"], 120)

            # 6. Atualizar descrição do chamado e conclusão
            tm.update_ticket_description(tid, "Descrição Final Atualizada do Chamado")
            tm.update_ticket_conclusion(tid, "Conclusão Técnica Final do Chamado")

            # 7. Finalizar chamado e gerar relatórios
            completed, html_path = tm.finish_active_ticket()
            self.assertTrue(Path(html_path).exists())
            doc_path = Path(html_path).parent / "relatorio_evidencias.doc"
            self.assertTrue(doc_path.exists())

            # 8. Valida conteúdo do HTML (incluindo controles do Modo Revisão Final)
            html_text = Path(html_path).read_text(encoding="utf-8")
            self.assertIn("Descrição Final Atualizada do Chamado", html_text)
            self.assertIn("Conclusão Técnica Final do Chamado", html_text)
            self.assertIn("Evidência Amarela Substituta", html_text)
            self.assertIn("Evidência Verde", html_text)
            self.assertIn('contenteditable="true"', html_text)
            self.assertIn("Evidência #01", html_text)
            self.assertIn("Evidência #02", html_text)
            self.assertIn("MODO REVISÃO FINAL", html_text)
            self.assertIn("moveCardUp", html_text)
            self.assertIn("moveCardDown", html_text)
            self.assertIn("replaceCardImage", html_text)
            self.assertIn("deleteCard", html_text)
            self.assertIn("saveRevisedHtml", html_text)

            # 9. Valida conteúdo do Word
            doc_text = doc_path.read_text(encoding="utf-8")
            self.assertIn("Descrição Final Atualizada do Chamado", doc_text)
            self.assertIn("Conclusão Técnica Final do Chamado", doc_text)
            self.assertIn("Evidência #01", doc_text)
            self.assertIn("Evidência #02", doc_text)

if __name__ == "__main__":
    unittest.main()
