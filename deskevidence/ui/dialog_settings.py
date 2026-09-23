from pathlib import Path
from typing import Optional, Callable
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from deskevidence.core.config_manager import ConfigManager, DEFAULT_HOTKEYS

class SettingsDialog(ctk.CTkToplevel):
    """
    Janela de configurações simplificada e completa do DeskEvidence.
    Permite customizar pasta padrão, atalhos de teclado e preferências de captura.
    """

    def __init__(
        self,
        parent,
        config_manager: ConfigManager,
        on_saved: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.config_mgr = config_manager
        self.on_saved_cb = on_saved

        self.title("DeskEvidence - Configurações")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        width = 540
        height = 620
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = int((screen_w - width) / 2)
        pos_y = int((screen_h - height) / 2)
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

        self._build_ui()

    def _build_ui(self):
        main_frame = ctk.CTkScrollableFrame(self, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Cabeçalho
        lbl_title = ctk.CTkLabel(
            main_frame,
            text="⚙️ Configurações do DeskEvidence",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(anchor="w", padx=12, pady=(10, 2))

        lbl_desc = ctk.CTkLabel(
            main_frame,
            text="Ajuste os atalhos de teclado, pasta padrão e modo de captura.",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        lbl_desc.pack(anchor="w", padx=12, pady=(0, 16))

        # --- SEÇÃO 1: PASTA PADRÃO ---
        sec_storage = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=8)
        sec_storage.pack(fill="x", padx=12, pady=(0, 14))

        ctk.CTkLabel(sec_storage, text="📁 Pasta Padrão de Evidências", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        
        folder_row = ctk.CTkFrame(sec_storage, fg_color="transparent")
        folder_row.pack(fill="x", padx=12, pady=(0, 10))

        self.entry_storage = ctk.CTkEntry(folder_row, height=34)
        self.entry_storage.insert(0, str(self.config_mgr.storage_folder))
        self.entry_storage.pack(side="left", fill="x", expand=True)

        btn_browse = ctk.CTkButton(
            folder_row,
            text="Procurar...",
            width=90,
            height=34,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self._browse_folder
        )
        btn_browse.pack(side="right", padx=(8, 0))

        # --- SEÇÃO 2: MODO DE CAPTURA ---
        sec_mode = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=8)
        sec_mode.pack(fill="x", padx=12, pady=(0, 14))

        ctk.CTkLabel(sec_mode, text="🎯 Modo de Captura Padrão", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        
        current_mode = self.config_mgr.get("capture_mode", "active_window")
        self.capture_mode_var = tk.StringVar(value=current_mode)

        rb_active = ctk.CTkRadioButton(
            sec_mode,
            text="Janela Ativa (Padrão recomendado - apenas o aplicativo em foco)",
            variable=self.capture_mode_var,
            value="active_window"
        )
        rb_active.pack(anchor="w", padx=16, pady=(4, 4))

        rb_full = ctk.CTkRadioButton(
            sec_mode,
            text="Tela Inteira (Área de trabalho completa / todos monitores)",
            variable=self.capture_mode_var,
            value="fullscreen"
        )
        rb_full.pack(anchor="w", padx=16, pady=(4, 12))

        # --- SEÇÃO 3: ATALHOS DE TECLADO ---
        sec_hotkeys = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=8)
        sec_hotkeys.pack(fill="x", padx=12, pady=(0, 14))

        ctk.CTkLabel(sec_hotkeys, text="⌨️ Atalhos de Teclado Globais", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(sec_hotkeys, text="Utilize combinações como ctrl+shift+e, ctrl+f10, alt+f9, etc.", font=ctk.CTkFont(size=11), text_color="gray70").pack(anchor="w", padx=12, pady=(0, 10))

        # Atalho Screenshot
        ctk.CTkLabel(sec_hotkeys, text="Tirar Screenshot da Evidência:").pack(anchor="w", padx=14, pady=(2, 2))
        self.entry_hk_capture = ctk.CTkEntry(sec_hotkeys, height=32)
        self.entry_hk_capture.insert(0, self.config_mgr.get_hotkey("capture"))
        self.entry_hk_capture.pack(fill="x", padx=14, pady=(0, 8))

        # Atalho Chamado/Projeto
        ctk.CTkLabel(sec_hotkeys, text="Ação de Chamado (Novo / Finalizar Ativo):").pack(anchor="w", padx=14, pady=(2, 2))
        self.entry_hk_ticket = ctk.CTkEntry(sec_hotkeys, height=32)
        self.entry_hk_ticket.insert(0, self.config_mgr.get_hotkey("ticket_action"))
        self.entry_hk_ticket.pack(fill="x", padx=14, pady=(0, 8))

        # Atalho Trocar Chamado
        ctk.CTkLabel(sec_hotkeys, text="Trocar Chamado Ativo:").pack(anchor="w", padx=14, pady=(2, 2))
        self.entry_hk_switch = ctk.CTkEntry(sec_hotkeys, height=32)
        self.entry_hk_switch.insert(0, self.config_mgr.get_hotkey("switch_ticket"))
        self.entry_hk_switch.pack(fill="x", padx=14, pady=(0, 8))

        # Atalho Configurações
        ctk.CTkLabel(sec_hotkeys, text="Abrir Tela de Configurações:").pack(anchor="w", padx=14, pady=(2, 2))
        self.entry_hk_settings = ctk.CTkEntry(sec_hotkeys, height=32)
        self.entry_hk_settings.insert(0, self.config_mgr.get_hotkey("open_settings"))
        self.entry_hk_settings.pack(fill="x", padx=14, pady=(0, 10))

        btn_reset_hk = ctk.CTkButton(
            sec_hotkeys,
            text="Restaurar Atalhos Padrão",
            height=28,
            fg_color="#475569",
            hover_color="#334155",
            command=self._reset_default_hotkeys
        )
        btn_reset_hk.pack(anchor="w", padx=14, pady=(0, 12))

        # --- SEÇÃO 4: PREFERÊNCIAS ADICIONAIS ---
        sec_pref = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=8)
        sec_pref.pack(fill="x", padx=12, pady=(0, 16))

        ctk.CTkLabel(sec_pref, text="✨ Preferências Gerais", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(10, 6))

        self.cb_prompt_var = tk.BooleanVar(value=bool(self.config_mgr.get("prompt_quick_note", True)))
        cb_prompt = ctk.CTkCheckBox(
            sec_pref,
            text="Abrir editor de marcações (estilo Lightshot) após captura",
            variable=self.cb_prompt_var
        )
        cb_prompt.pack(anchor="w", padx=16, pady=(4, 6))

        self.cb_html_var = tk.BooleanVar(value=bool(self.config_mgr.get("generate_html_on_finish", True)))
        cb_html = ctk.CTkCheckBox(
            sec_pref,
            text="Gerar relatório consolidado HTML ao finalizar chamado",
            variable=self.cb_html_var
        )
        cb_html.pack(anchor="w", padx=16, pady=(4, 12))

        # --- BOTÕES SALVAR / CANCELAR ---
        btn_row = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(8, 14))

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Cancelar",
            fg_color="#64748b",
            hover_color="#475569",
            width=100,
            command=self.destroy
        )
        btn_cancel.pack(side="left")

        btn_save = ctk.CTkButton(
            btn_row,
            text="Salvar Alterações",
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(weight="bold"),
            command=self._do_save
        )
        btn_save.pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _browse_folder(self):
        curr = self.entry_storage.get().strip()
        selected = filedialog.askdirectory(initialdir=curr, parent=self)
        if selected:
            self.entry_storage.delete(0, "end")
            self.entry_storage.insert(0, selected)

    def _reset_default_hotkeys(self):
        self.entry_hk_capture.delete(0, "end")
        self.entry_hk_capture.insert(0, DEFAULT_HOTKEYS["capture"])

        self.entry_hk_ticket.delete(0, "end")
        self.entry_hk_ticket.insert(0, DEFAULT_HOTKEYS["ticket_action"])

        self.entry_hk_switch.delete(0, "end")
        self.entry_hk_switch.insert(0, DEFAULT_HOTKEYS["switch_ticket"])

        self.entry_hk_settings.delete(0, "end")
        self.entry_hk_settings.insert(0, DEFAULT_HOTKEYS["open_settings"])

    def _do_save(self):
        folder = self.entry_storage.get().strip()
        if not folder:
            messagebox.showwarning("Aviso", "Informe um caminho para a pasta padrão.", parent=self)
            return

        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Erro de Pasta", f"Não foi possível acessar ou criar a pasta indicada:\n{e}", parent=self)
            return

        self.config_mgr.set("storage_folder", folder)
        self.config_mgr.set("capture_mode", self.capture_mode_var.get())
        self.config_mgr.set("prompt_quick_note", self.cb_prompt_var.get())
        self.config_mgr.set("generate_html_on_finish", self.cb_html_var.get())

        self.config_mgr.set_hotkey("capture", self.entry_hk_capture.get().strip().lower())
        self.config_mgr.set_hotkey("ticket_action", self.entry_hk_ticket.get().strip().lower())
        self.config_mgr.set_hotkey("switch_ticket", self.entry_hk_switch.get().strip().lower())
        self.config_mgr.set_hotkey("open_settings", self.entry_hk_settings.get().strip().lower())

        messagebox.showinfo("Sucesso", "Configurações salvas e aplicadas com sucesso!", parent=self)

        if self.on_saved_cb:
            self.on_saved_cb()

        self.destroy()
