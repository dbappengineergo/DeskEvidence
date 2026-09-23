import os
from pathlib import Path
from typing import Callable, Optional
from PIL import Image
import pystray
from pystray import MenuItem as item

from deskevidence.core.ticket_manager import TicketManager

class TrayController:
    """
    Controlador da presença em segundo plano no System Tray do Windows (bandeja do sistema).
    """

    def __init__(
        self,
        ticket_manager: TicketManager,
        on_capture: Callable[[], None],
        on_ticket_action: Callable[[], None],
        on_switch_ticket: Callable[[], None],
        on_finish_ticket: Callable[[], None],
        on_export_pdf: Optional[Callable[[], None]] = None,
        on_export_word: Optional[Callable[[], None]] = None,
        on_open_folder: Callable[[], None] = lambda: None,
        on_open_settings: Callable[[], None] = lambda: None,
        on_exit: Callable[[], None] = lambda: None
    ):
        self.ticket_mgr = ticket_manager
        self.on_capture = on_capture
        self.on_ticket_action = on_ticket_action
        self.on_switch_ticket = on_switch_ticket
        self.on_finish_ticket = on_finish_ticket
        self.on_export_pdf = on_export_pdf
        self.on_export_word = on_export_word
        self.on_open_folder = on_open_folder
        self.on_open_settings = on_open_settings
        self.on_exit = on_exit

        self.assets_dir = Path(__file__).parent.parent / "assets"
        self._icon: Optional[pystray.Icon] = None
        self._load_images()

    def _load_images(self):
        try:
            icon_path = self.assets_dir / "icon.png"
            icon_active_path = self.assets_dir / "icon_active.png"
            self.image_idle = Image.open(str(icon_path))
            self.image_active = Image.open(str(icon_active_path))
        except Exception:
            # Fallback dinâmico se os arquivos de imagem não forem encontrados
            from deskevidence.assets.generate_icons import create_app_icon
            self.image_idle = create_app_icon(is_active=False)
            self.image_active = create_app_icon(is_active=True)

    def _get_current_image(self) -> Image.Image:
        active = self.ticket_mgr.get_active_ticket()
        return self.image_active if active else self.image_idle

    def _get_tooltip(self) -> str:
        active = self.ticket_mgr.get_active_ticket()
        if active:
            return f"DeskEvidence - Chamado Ativo: #{active.get('number')} ({active.get('name')[:25]})"
        return "DeskEvidence - Nenhum chamado ativo (Aguardando)"

    def _create_menu(self) -> pystray.Menu:
        active = self.ticket_mgr.get_active_ticket()

        if active:
            header_text = f"● Ativo: #{active.get('number')} ({len(active.get('evidences', []))} fotos)"
        else:
            header_text = "○ Nenhum chamado ativo"

        menu_items = [
            item(header_text, lambda: self.on_ticket_action(), default=True),
            pystray.Menu.SEPARATOR,
            item("Capturar Evidência Agora", lambda: self.on_capture()),
            item("Salvar Relatório em PDF / Imprimir", lambda: self.on_export_pdf() if self.on_export_pdf else None, enabled=lambda _: bool(self.ticket_mgr.get_active_ticket())),
            item("Salvar Relatório em Word (.doc)", lambda: self.on_export_word() if self.on_export_word else None, enabled=lambda _: bool(self.ticket_mgr.get_active_ticket())),
            pystray.Menu.SEPARATOR,
            item("Finalizar Chamado Atual...", lambda: self.on_finish_ticket(), enabled=lambda _: bool(self.ticket_mgr.get_active_ticket())),
            item("Novo Chamado / Projeto...", lambda: self.on_ticket_action()),
            item("Trocar Chamado...", lambda: self.on_switch_ticket()),
            pystray.Menu.SEPARATOR,
            item("Abrir Pasta das Evidências", lambda: self.on_open_folder()),
            item("Configurações...", lambda: self.on_open_settings()),
            pystray.Menu.SEPARATOR,
            item("Sair do DeskEvidence", lambda: self.on_exit()),
        ]
        return pystray.Menu(*menu_items)

    def start(self):
        """Inicia o ícone do System Tray em modo detached."""
        self._icon = pystray.Icon(
            name="DeskEvidence",
            icon=self._get_current_image(),
            title=self._get_tooltip(),
            menu=self._create_menu()
        )
        self._icon.run_detached()

    def update_state(self):
        """Atualiza o ícone, o menu de contexto e o tooltip de acordo com o estado do chamado."""
        if self._icon:
            self._icon.icon = self._get_current_image()
            self._icon.title = self._get_tooltip()
            self._icon.menu = self._create_menu()

    def notify(self, message: str, title: str = "DeskEvidence"):
        """Exibe uma notificação balão/toast do Windows."""
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    def stop(self):
        """Remove o ícone da bandeja."""
        if self._icon:
            self._icon.stop()
            self._icon = None
