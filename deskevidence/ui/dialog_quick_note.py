import tkinter as tk
from typing import Optional, Callable
from PIL import Image
import customtkinter as ctk

class QuickNoteDialog(ctk.CTkToplevel):
    """
    Janela leve e rápida que surge após a captura da evidência
    para que o usuário informe uma breve descrição.
    """

    def __init__(
        self,
        parent: tk.Tk,
        image: Image.Image,
        metadata: dict,
        ticket_number: str,
        on_save: Callable[[str], None],
        on_cancel: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.on_save_cb = on_save
        self.on_cancel_cb = on_cancel
        self.saved = False

        self.title("DeskEvidence - Anotar Evidência")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        # Configura dimensões
        width = 460
        height = 420

        # Centraliza na tela
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = int((screen_w - width) / 2)
        pos_y = int((screen_h - height) / 2)
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

        # Estilo do frame principal
        self.main_frame = ctk.CTkFrame(self, corner_radius=12)
        self.main_frame.pack(fill="both", expand=True, padx=14, pady=14)

        # Cabeçalho
        lbl_header = ctk.CTkLabel(
            self.main_frame,
            text=f"📸 Nova Evidência - Chamado {ticket_number}",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        lbl_header.pack(anchor="w", padx=12, pady=(10, 2))

        # Título da janela ativa
        win_title = metadata.get("window_title", "Janela Ativa")
        if len(win_title) > 55:
            win_title = win_title[:52] + "..."
        lbl_sub = ctk.CTkLabel(
            self.main_frame,
            text=f"Janela: {win_title}",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        lbl_sub.pack(anchor="w", padx=12, pady=(0, 8))

        # Miniatura da imagem capturada
        thumb_img = image.copy()
        thumb_img.thumbnail((420, 180))
        self.ctk_thumb = ctk.CTkImage(light_image=thumb_img, dark_image=thumb_img, size=thumb_img.size)
        lbl_image = ctk.CTkLabel(self.main_frame, image=self.ctk_thumb, text="")
        lbl_image.pack(padx=12, pady=4)

        # Campo de descrição
        lbl_desc = ctk.CTkLabel(
            self.main_frame,
            text="Descrição breve da ação (opcional):",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_desc.pack(anchor="w", padx=12, pady=(8, 2))

        self.entry_desc = ctk.CTkEntry(
            self.main_frame,
            placeholder_text="Ex: Clique no botão emitir, validação de mensagem...",
            height=36,
            font=ctk.CTkFont(size=13)
        )
        self.entry_desc.pack(fill="x", padx=12, pady=(0, 6))

        # Atalhos de teclado
        self.entry_desc.bind("<Return>", lambda e: self._action_save())
        self.bind("<Escape>", lambda e: self._action_cancel())

        # Botões de Ação
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(10, 6))

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Descartar (Esc)",
            fg_color="#ef4444",
            hover_color="#dc2626",
            width=110,
            command=self._action_cancel
        )
        btn_cancel.pack(side="left")

        btn_save = ctk.CTkButton(
            btn_frame,
            text="Salvar Evidência [Enter]",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._action_save
        )
        btn_save.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Foco imediato no campo de texto
        self.after(100, self._focus_entry)
        self.protocol("WM_DELETE_WINDOW", self._action_cancel)

    def _focus_entry(self):
        self.lift()
        self.focus_force()
        self.entry_desc.focus_set()

    def _action_save(self):
        if self.saved:
            return
        self.saved = True
        desc = self.entry_desc.get().strip()
        self.destroy()
        if self.on_save_cb:
            self.on_save_cb(desc)

    def _action_cancel(self):
        if self.saved:
            return
        self.saved = True
        self.destroy()
        if self.on_cancel_cb:
            self.on_cancel_cb()
