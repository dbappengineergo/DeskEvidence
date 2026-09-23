import os
import re
import json
import shutil
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from PIL import Image

from deskevidence.core.config_manager import ConfigManager
from deskevidence.core.report_builder import generate_html_report, generate_word_report

def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos e pastas no Windows."""
    # Proibidos no Windows: < > : " / \ | ? *
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    cleaned = cleaned.strip('. ')
    return cleaned if cleaned else "sem_nome"

class TicketManager:
    """Gerenciador do ciclo de vida dos Chamados/Projetos e armazenamento de evidências."""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self._active_ticket: Optional[Dict[str, Any]] = None
        self._load_active_ticket()

    @property
    def base_storage_folder(self) -> Path:
        return self.config.storage_folder

    def _load_active_ticket(self):
        active_id = self.config.get("last_active_ticket_id")
        if active_id:
            ticket = self.get_ticket_by_id(active_id)
            if ticket and ticket.get("status") == "active":
                self._active_ticket = ticket
            else:
                self.config.set("last_active_ticket_id", None)
                self._active_ticket = None

    def get_active_ticket(self) -> Optional[Dict[str, Any]]:
        return self._active_ticket

    def set_active_ticket(self, ticket_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not ticket_id:
            self._active_ticket = None
            self.config.set("last_active_ticket_id", None)
            return None

        ticket = self.get_ticket_by_id(ticket_id)
        if ticket:
            # Reativa o chamado caso tenha sido finalizado anteriormente
            ticket["status"] = "active"
            ticket["closed_at"] = None
            ticket["closed_at_display"] = None
            self._save_ticket_json(ticket)
            self._active_ticket = ticket
            self.config.set("last_active_ticket_id", ticket_id)
        return self._active_ticket

    def create_ticket(self, number: str, name: str, description: str = "") -> Dict[str, Any]:
        """Cria um novo chamado/projeto e o define como ativo."""
        now = datetime.datetime.now()
        ticket_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{sanitize_filename(number)}"

        # Nome da pasta: [NUMERO] - [NOME]
        clean_number = sanitize_filename(number)
        clean_name = sanitize_filename(name)
        folder_name = f"[{clean_number}] - {clean_name}"
        folder_path = self.base_storage_folder / folder_name

        # Evita colisão se já existir pasta homônima
        counter = 1
        original_folder_path = folder_path
        while folder_path.exists():
            folder_path = self.base_storage_folder / f"{original_folder_path.name}_{counter}"
            counter += 1

        folder_path.mkdir(parents=True, exist_ok=True)
        evidencias_folder = folder_path / "evidencias"
        evidencias_folder.mkdir(parents=True, exist_ok=True)

        ticket_data = {
            "id": ticket_id,
            "number": number.strip(),
            "name": name.strip(),
            "description": description.strip(),
            "status": "active",
            "created_at": now.isoformat(),
            "created_at_display": now.strftime("%d/%m/%Y %H:%M:%S"),
            "closed_at": None,
            "closed_at_display": None,
            "folder_path": str(folder_path),
            "evidences": []
        }

        self._save_ticket_json(ticket_data)
        self._active_ticket = ticket_data
        self.config.set("last_active_ticket_id", ticket_id)

        return ticket_data

    def _save_ticket_json(self, ticket_data: Dict[str, Any]):
        folder = Path(ticket_data["folder_path"])
        ticket_file = folder / "ticket.json"
        with open(ticket_file, "w", encoding="utf-8") as f:
            json.dump(ticket_data, f, indent=4, ensure_ascii=False)

    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        for ticket in self.list_tickets():
            if ticket.get("id") == ticket_id:
                return ticket
        return None

    def list_tickets(self) -> List[Dict[str, Any]]:
        """Varre a pasta base e lista todos os chamados existentes."""
        tickets = []
        if not self.base_storage_folder.exists():
            return tickets

        for item in self.base_storage_folder.iterdir():
            if item.is_dir():
                ticket_json = item / "ticket.json"
                if ticket_json.exists():
                    try:
                        with open(ticket_json, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            # Atualiza folder_path caso a pasta tenha sido movida
                            data["folder_path"] = str(item)
                            tickets.append(data)
                    except Exception:
                        pass
        
        # Ordena do mais recente para o mais antigo
        tickets.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return tickets

    def save_evidence(self, image: Image.Image, metadata: Dict[str, Any], description: str = "") -> Optional[Dict[str, Any]]:
        """Salva a evidência no chamado ativo."""
        if not self._active_ticket:
            return None

        folder = Path(self._active_ticket["folder_path"])
        evidencias_folder = folder / "evidencias"
        evidencias_folder.mkdir(parents=True, exist_ok=True)

        evidences = self._active_ticket.get("evidences", [])
        next_idx = len(evidences) + 1

        now = datetime.datetime.now()
        timestamp_slug = now.strftime("%Y%m%d_%H%M%S")
        proc_slug = sanitize_filename(metadata.get("process_name", "app")).replace(".exe", "")
        filename = f"{next_idx:03d}_{timestamp_slug}_{proc_slug}.png"
        filepath = evidencias_folder / filename

        # Salva o arquivo de imagem
        image.save(str(filepath), "PNG", optimize=True)

        evidence_record = {
            "index": next_idx,
            "filename": filename,
            "relative_path": f"evidencias/{filename}",
            "description": description.strip(),
            "timestamp": metadata.get("timestamp", now.isoformat()),
            "timestamp_display": metadata.get("timestamp_display", now.strftime("%d/%m/%Y %H:%M:%S")),
            "window_title": metadata.get("window_title", ""),
            "process_name": metadata.get("process_name", ""),
            "mode": metadata.get("mode", "active_window"),
            "width": metadata.get("width", image.width),
            "height": metadata.get("height", image.height),
        }

        evidences.append(evidence_record)
        self._active_ticket["evidences"] = evidences
        self._save_ticket_json(self._active_ticket)

        return evidence_record

    def update_ticket_conclusion(self, ticket_id: str, conclusion: str) -> bool:
        """Atualiza a conclusão textual do chamado e salva no JSON."""
        ticket = self.get_ticket_by_id(ticket_id)
        if not ticket:
            return False
        ticket["conclusion"] = conclusion.strip()
        self._save_ticket_json(ticket)
        if self._active_ticket and self._active_ticket.get("id") == ticket_id:
            self._active_ticket["conclusion"] = conclusion.strip()
        return True

    def finish_active_ticket(self, conclusion: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Finaliza o chamado ativo e gera o relatório consolidado em HTML."""
        if not self._active_ticket:
            return None, None

        now = datetime.datetime.now()
        self._active_ticket["status"] = "completed"
        self._active_ticket["closed_at"] = now.isoformat()
        self._active_ticket["closed_at_display"] = now.strftime("%d/%m/%Y %H:%M:%S")
        if conclusion is not None:
            self._active_ticket["conclusion"] = conclusion.strip()

        folder = Path(self._active_ticket["folder_path"])
        self._save_ticket_json(self._active_ticket)

        # Gera o relatório HTML consolidado (com botões PDF e Word integrados)
        html_path = folder / "relatorio_evidencias.html"
        generate_html_report(self._active_ticket, html_path)

        # Gera também o arquivo de relatório em formato Word (.doc) diretamente na pasta
        doc_path = folder / "relatorio_evidencias.doc"
        try:
            generate_word_report(self._active_ticket, doc_path)
        except Exception as e:
            print(f"[TicketManager] Falha ao gerar arquivo Word (.doc): {e}")

        completed_ticket = dict(self._active_ticket)
        # Desativa o chamado atual
        self._active_ticket = None
        self.config.set("last_active_ticket_id", None)

        return completed_ticket, str(html_path)

    def delete_ticket(self, ticket_id: str, delete_files: bool = False) -> bool:
        """Exclui ou cancela um chamado."""
        ticket = self.get_ticket_by_id(ticket_id)
        if not ticket:
            return False

        if self._active_ticket and self._active_ticket.get("id") == ticket_id:
            self.set_active_ticket(None)

        if delete_files:
            folder = Path(ticket["folder_path"])
            if folder.exists():
                try:
                    shutil.rmtree(folder)
                    return True
                except Exception as e:
                    print(f"[TicketManager] Falha ao deletar pasta {folder}: {e}")
                    return False
        return True

    def export_reports(self, ticket_data: Optional[Dict[str, Any]] = None, conclusion: Optional[str] = None) -> Tuple[str, str]:
        """Gera ou atualiza os relatórios HTML (com botão PDF/Word) e Word (.doc) do chamado."""
        target = ticket_data or self._active_ticket
        if not target:
            raise ValueError("Nenhum chamado ativo ou informado para exportação.")

        if conclusion is not None:
            target["conclusion"] = conclusion.strip()
            self._save_ticket_json(target)

        folder = Path(target["folder_path"])
        html_path = folder / "relatorio_evidencias.html"
        doc_path = folder / "relatorio_evidencias.doc"

        generate_html_report(target, html_path)
        generate_word_report(target, doc_path)

        return str(html_path), str(doc_path)
