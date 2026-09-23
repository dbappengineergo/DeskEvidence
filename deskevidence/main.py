import sys
import os
import ctypes
from pathlib import Path
from datetime import datetime

# Garante que sys.stdout e sys.stderr existam em modo GUI sem console
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

def log_debug(msg: str):
    try:
        log_file = Path.home() / "DeskEvidence_debug.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

# Garante que o diretório raiz do projeto esteja no sys.path
_current_dir = Path(__file__).resolve().parent
_repo_root = _current_dir.parent
for _p in (str(_repo_root), str(_current_dir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from typing import Optional
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import win32event
import win32api
import winerror

from deskevidence.core.config_manager import ConfigManager
from deskevidence.core.ticket_manager import TicketManager
from deskevidence.core.capture_engine import CaptureEngine
from deskevidence.core.hotkey_manager import HotkeyManager
from deskevidence.ui.tray_controller import TrayController
from deskevidence.ui.dialog_ticket import TicketDialog
from deskevidence.ui.dialog_quick_note import QuickNoteDialog
from deskevidence.ui.dialog_settings import SettingsDialog
from deskevidence.ui.dialog_editor import EvidenceEditorDialog

# Configuração visual do tema do CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class DeskEvidenceApp:
    """Aplicação Principal DeskEvidence."""
    def __init__(self):
        log_debug(f"DeskEvidenceApp __init__ started (PID: {os.getpid()})")
        # 1. Single Instance Lock via Windows Mutex (escopo de sessão do usuário)
        self.mutex_name = "Local\\DeskEvidence_SingleInstance_Mutex_Weder"
        self.mutex = win32event.CreateMutex(None, False, self.mutex_name)
        last_err = win32api.GetLastError()
        log_debug(f"CreateMutex result: last_err={last_err}")
        if last_err == winerror.ERROR_ALREADY_EXISTS:
            log_debug("ERROR_ALREADY_EXISTS detectado! Exibindo aviso e encerrando.")
            ctypes.windll.user32.MessageBoxW(
                0,
                "O DeskEvidence já está em execução no System Tray (bandeja do sistema).",
                "DeskEvidence Já Aberto",
                0x40  # MB_ICONINFORMATION
            )
            sys.exit(0)
        log_debug("Mutex adquirido com sucesso.")

        # 2. Inicialização do Loop Tkinter (Oculto na Barra de Tarefas)
        self.root = ctk.CTk()
        self.root.withdraw()  # Oculta a janela principal do desktop

        # 3. Inicialização dos Módulos Core
        self.config_mgr = ConfigManager()
        self.ticket_mgr = TicketManager(self.config_mgr)
        self.capture_engine = CaptureEngine(mode=self.config_mgr.get("capture_mode", "active_window"))
        self.hotkey_mgr = HotkeyManager()

        # Janelas modais ativas (para evitar abrir duplicadas)
        self._current_dialog: Optional[ctk.CTkToplevel] = None
        self._editor_dialog: Optional[EvidenceEditorDialog] = None

        # 4. Inicialização do Controlador de Bandeja (System Tray)
        self.tray = TrayController(
            ticket_manager=self.ticket_mgr,
            on_capture=lambda: self.dispatch_to_main_thread(self.trigger_capture),
            on_ticket_action=lambda: self.dispatch_to_main_thread(self.open_ticket_dialog, "auto"),
            on_switch_ticket=lambda: self.dispatch_to_main_thread(self.open_ticket_dialog, "switch"),
            on_finish_ticket=lambda: self.dispatch_to_main_thread(self.finish_active_ticket),
            on_export_pdf=lambda: self.dispatch_to_main_thread(self.export_active_pdf),
            on_export_word=lambda: self.dispatch_to_main_thread(self.export_active_word),
            on_open_folder=lambda: self.dispatch_to_main_thread(self.open_evidence_folder),
            on_open_settings=lambda: self.dispatch_to_main_thread(self.open_settings_dialog),
            on_exit=lambda: self.dispatch_to_main_thread(self.exit_app)
        )

        # 5. Configuração e Registro das Teclas de Atalho
        self.register_all_hotkeys()
        self.hotkey_mgr.start()

    def dispatch_to_main_thread(self, func, *args, **kwargs):
        """Encaminha comandos de outras threads para a thread principal da UI com segurança."""
        def _safe_call():
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(f"[DeskEvidence] Erro na execução da thread principal: {e}")
                import traceback
                traceback.print_exc()

        try:
            self.root.after(0, _safe_call)
        except Exception as e:
            print(f"[DeskEvidence] Falha ao agendar na thread principal: {e}")

    def register_all_hotkeys(self):
        """Registra todos os atalhos configurados no HotkeyManager."""
        self.hotkey_mgr.unregister_all()

        hk_capture = self.config_mgr.get_hotkey("capture")
        hk_ticket = self.config_mgr.get_hotkey("ticket_action")
        hk_switch = self.config_mgr.get_hotkey("switch_ticket")
        hk_settings = self.config_mgr.get_hotkey("open_settings")

        if hk_capture:
            self.hotkey_mgr.register_hotkey(
                hk_capture,
                lambda: self.dispatch_to_main_thread(self.trigger_capture)
            )

        if hk_ticket:
            self.hotkey_mgr.register_hotkey(
                hk_ticket,
                lambda: self.dispatch_to_main_thread(self.open_ticket_dialog, "auto")
            )

        if hk_switch:
            self.hotkey_mgr.register_hotkey(
                hk_switch,
                lambda: self.dispatch_to_main_thread(self.open_ticket_dialog, "switch")
            )

        if hk_settings:
            self.hotkey_mgr.register_hotkey(
                hk_settings,
                lambda: self.dispatch_to_main_thread(self.open_settings_dialog)
            )

    # --- AÇÕES DO APLICATIVO ---

    def trigger_capture(self):
        """Executado quando a tecla de screenshot é pressionada ou pelo menu do tray."""
        active_ticket = self.ticket_mgr.get_active_ticket()

        # Se não houver chamado ativo, convida o usuário a criar um
        if not active_ticket:
            self.tray.notify(
                "Nenhum chamado ativo! Crie ou selecione um chamado para vincular as evidências.",
                "DeskEvidence - Chamado Necessário"
            )
            self.open_ticket_dialog(mode="create")
            return

        # Se já houver um EDITOR de evidências em andamento, traz para a frente (não sobrepõe outro print)
        if self._editor_dialog:
            try:
                if self._editor_dialog.winfo_exists():
                    self._editor_dialog.lift()
                    self._editor_dialog.focus_force()
                    return
            except Exception:
                self._editor_dialog = None

        # Se houver diálogo de chamado ou configurações aberto em segundo plano, fecha-o
        # para que o usuário capture a janela desejada livremente sem interferência
        if self._current_dialog:
            try:
                if self._current_dialog.winfo_exists():
                    self._current_dialog.destroy()
            except Exception:
                pass
            self._current_dialog = None

        # Atualiza modo configurado
        mode = self.config_mgr.get("capture_mode", "active_window")
        self.capture_engine.mode = mode

        # Executa o screenshot da janela ativa ou tela inteira
        capture_result = self.capture_engine.capture()
        if not capture_result:
            self.tray.notify("Não foi possível capturar a janela ativa.", "Erro de Captura")
            return

        # Abre o Editor de Evidências estilo Lightshot
        # Regra de negócio: A evidência SOMENTE é salva após o usuário realizar as marcações e clicar em Salvar
        def on_save(edited_image, note_text: str):
            self._editor_dialog = None
            saved = self.ticket_mgr.save_evidence(
                edited_image,
                capture_result.metadata,
                description=note_text
            )
            self.tray.update_state()
            if saved:
                idx = saved.get("index", 1)
                self.tray.notify(
                    f"Evidência #{idx:02d} vinculada ao chamado #{active_ticket.get('number')}!",
                    "Evidência Salva com Sucesso"
                )

        def on_cancel():
            self._editor_dialog = None
            print("[DeskEvidence] Captura descartada pelo usuário sem salvar.")

        self._editor_dialog = EvidenceEditorDialog(
            parent=self.root,
            image=capture_result.image,
            metadata=capture_result.metadata,
            ticket_number=active_ticket.get("number", ""),
            on_save=on_save,
            on_cancel=on_cancel
        )

    def open_ticket_dialog(self, mode: str = "auto"):
        """Abre o diálogo de criação, gerenciamento ou troca de chamado."""
        if self._current_dialog:
            try:
                if self._current_dialog.winfo_exists():
                    self._current_dialog.lift()
                    self._current_dialog.focus_force()
                    return
            except Exception:
                self._current_dialog = None

        def on_changed():
            self.tray.update_state()

        self._current_dialog = TicketDialog(
            parent=self.root,
            ticket_manager=self.ticket_mgr,
            mode=mode,
            on_ticket_changed=on_changed
        )

    def finish_active_ticket(self):
        """Finaliza o chamado ativo a partir do menu do tray."""
        active = self.ticket_mgr.get_active_ticket()
        if not active:
            return

        confirm = messagebox.askyesno(
            "Finalizar Chamado",
            f"Deseja finalizar o chamado #{active.get('number')}?\nUm relatório HTML consolidado será gerado automaticamente.",
            parent=self.root
        )
        if not confirm:
            return

        ticket, report_path = self.ticket_mgr.finish_active_ticket()
        self.tray.update_state()

        self.tray.notify(
            f"Chamado #{ticket.get('number')} finalizado e relatório HTML gerado!",
            "Chamado Concluído"
        )

        if report_path and Path(report_path).exists():
            os.startfile(report_path)

    def export_active_pdf(self):
        """Gera e abre o relatório do chamado ativo em PDF/HTML para impressão imediata."""
        active = self.ticket_mgr.get_active_ticket()
        if not active:
            self.tray.notify("Nenhum chamado ativo no momento.", "DeskEvidence")
            return
        try:
            html_path, _ = self.ticket_mgr.export_reports(active)
            if html_path and Path(html_path).exists():
                os.startfile(html_path)
        except Exception as e:
            self.tray.notify(f"Falha ao gerar relatório: {e}", "Erro na Exportação")

    def export_active_word(self):
        """Gera e abre o relatório do chamado ativo diretamente no Microsoft Word (.doc)."""
        active = self.ticket_mgr.get_active_ticket()
        if not active:
            self.tray.notify("Nenhum chamado ativo no momento.", "DeskEvidence")
            return
        try:
            _, doc_path = self.ticket_mgr.export_reports(active)
            if doc_path and Path(doc_path).exists():
                os.startfile(doc_path)
        except Exception as e:
            self.tray.notify(f"Falha ao gerar arquivo Word: {e}", "Erro na Exportação")

    def open_evidence_folder(self):
        """Abre a pasta do chamado ativo ou a pasta padrão de evidências."""
        active = self.ticket_mgr.get_active_ticket()
        if active and active.get("folder_path"):
            target_path = Path(active["folder_path"])
        else:
            target_path = self.ticket_mgr.base_storage_folder

        if target_path.exists():
            os.startfile(str(target_path))
        else:
            target_path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(target_path))

    def open_settings_dialog(self):
        """Abre a janela de configurações."""
        if self._current_dialog:
            try:
                if self._current_dialog.winfo_exists():
                    self._current_dialog.lift()
                    self._current_dialog.focus_force()
                    return
            except Exception:
                self._current_dialog = None

        def on_saved():
            self.register_all_hotkeys()
            self.tray.update_state()

        self._current_dialog = SettingsDialog(
            parent=self.root,
            config_manager=self.config_mgr,
            on_saved=on_saved
        )

    def exit_app(self):
        """Encerra a aplicação de forma graciosa."""
        try:
            self.hotkey_mgr.stop()
        except Exception:
            pass

        try:
            self.tray.stop()
        except Exception:
            pass

        try:
            self.root.destroy()
        except Exception:
            pass

        sys.exit(0)

    def run(self):
        """Inicia o aplicativo e seu loop de eventos."""
        log_debug("run() chamado. Iniciando System Tray...")
        self.tray.start()
        log_debug("System Tray iniciado. Disparando notificação inicial...")

        # Notificação de boas-vindas na bandeja
        self.tray.notify(
            f"DeskEvidence ativo no System Tray!\nAtalho Captura: {self.config_mgr.get_hotkey('capture')}\nAtalho Chamados: {self.config_mgr.get_hotkey('ticket_action')}",
            "DeskEvidence Iniciado"
        )
        log_debug("Entrando no loop principal (root.mainloop)...")
        # Executa o loop do Tkinter
        self.root.mainloop()
        log_debug("root.mainloop finalizado.")


def main():
    log_debug(f"main() iniciado no processo PID: {os.getpid()}")
    try:
        app = DeskEvidenceApp()
        app.run()
    except BaseException as e:
        log_debug(f"Exceção capturada em main(): {type(e).__name__}: {e}")
        import traceback
        err_msg = traceback.format_exc()
        try:
            with open(Path.home() / "DeskEvidence_crash.log", "w", encoding="utf-8") as f:
                f.write(err_msg)
        except Exception:
            pass
        if not isinstance(e, SystemExit):
            try:
                ctypes.windll.user32.MessageBoxW(0, f"Erro ao executar DeskEvidence:\n{err_msg}", "Erro DeskEvidence", 0x10)
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
