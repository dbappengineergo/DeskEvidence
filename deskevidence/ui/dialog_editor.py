import math
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, List, Tuple
from PIL import Image, ImageTk
import customtkinter as ctk

from deskevidence.core.annotation_engine import (
    AnnotationAction,
    render_annotations,
    copy_image_to_clipboard
)

# Paleta de cores rápidas (estilo Lightshot)
PALETTE_COLORS = [
    ("#ef4444", "Vermelho"),
    ("#f97316", "Laranja"),
    ("#eab308", "Amarelo"),
    ("#22c55e", "Verde"),
    ("#3b82f6", "Azul"),
    ("#a855f7", "Roxo"),
    ("#ffffff", "Branco"),
    ("#0f172a", "Preto"),
]

STROKE_WIDTHS = [
    (2, "Fino"),
    (4, "Médio"),
    (7, "Grosso"),
]


class EvidenceEditorDialog(ctk.CTkToplevel):
    """
    Janela interativa de edição e anotação de evidências estilo Lightshot.
    Permite desenhar caixas, setas, caneta, marca-texto, textos, números e recorte.
    A evidência SOMENTE é salva no chamado após o usuário confirmar explicitamente.
    """

    def __init__(
        self,
        parent: tk.Tk,
        image: Image.Image,
        metadata: dict,
        ticket_number: str,
        on_save: Callable[[Image.Image, str], None],
        on_cancel: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.original_image = image
        self.metadata = metadata
        self.ticket_number = ticket_number
        self.on_save_cb = on_save
        self.on_cancel_cb = on_cancel

        self.saved_or_cancelled = False

        # Estado da edição
        self.history: List[AnnotationAction] = []
        self.redo_stack: List[AnnotationAction] = []
        self.crop_box: Optional[Tuple[int, int, int, int]] = None

        # Ferramentas: 'rect', 'arrow', 'pen', 'line', 'highlight', 'text', 'badge', 'crop'
        self.current_tool = "rect"
        self.current_color = "#ef4444"  # Vermelho padrão
        self.current_width = 4          # Médio padrão
        self.badge_counter = 1

        # Cache de renderização
        self.display_image_tk: Optional[ImageTk.PhotoImage] = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Rastreamento de arraste do mouse
        self.is_dragging = False
        self.drag_start_img: Optional[Tuple[float, float]] = None
        self.current_drag_points: List[Tuple[float, float]] = []
        self.preview_item_id = None
        self.preview_extra_id = None

        # Widget de texto inline ativo
        self.active_text_entry = None
        self.active_text_coords = None

        self._init_window()
        self._build_ui()
        self._bind_events()

        # Render inicial após estabilização do layout
        self.after(50, self._update_canvas_view)

    def _init_window(self):
        self.title(f"DeskEvidence - Editor de Evidência [Chamado #{self.ticket_number}]")
        self.attributes("-topmost", True)

        # Dimensionamento inteligente: 90% da tela ou resolução original adaptada
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        target_w = min(int(screen_w * 0.92), max(960, self.original_image.width + 120))
        target_h = min(int(screen_h * 0.88), max(680, self.original_image.height + 180))

        pos_x = max(0, int((screen_w - target_w) / 2))
        pos_y = max(0, int((screen_h - target_h) / 2))

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        self.minsize(820, 560)

    def _build_ui(self):
        self.configure(fg_color="#0f172a")

        # Container Principal
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=(8, 10))

        # 1. BARRA SUPERIOR (TOOLBAR LIGHTSHOT)
        self._build_top_toolbar()

        # 2. ÁREA CENTRAL (CANVAS COM IMAGEM)
        self.canvas_frame = ctk.CTkFrame(self.main_container, fg_color="#182234", corner_radius=8)
        self.canvas_frame.pack(fill="both", expand=True, pady=6)

        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg="#111827",
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # 3. BARRA INFERIOR (DESCRIÇÃO E AÇÕES FINAIS)
        self._build_bottom_bar()

    def _build_top_toolbar(self):
        self.toolbar_frame = ctk.CTkFrame(self.main_container, fg_color="#1e293b", corner_radius=8, height=48)
        self.toolbar_frame.pack(fill="x", pady=(0, 4))

        # Grupo de Ferramentas
        tools_frame = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        tools_frame.pack(side="left", padx=8, pady=4)

        self.tool_buttons = {}
        tool_specs = [
            ("rect", "🔲 Retângulo (R)", "Retângulo"),
            ("arrow", "↗️ Seta (A)", "Seta"),
            ("pen", "✏️ Caneta (P)", "Caneta"),
            ("line", "📏 Linha (L)", "Linha"),
            ("highlight", "🖍️ Marca-texto (H)", "Marca-texto"),
            ("text", "🔤 Texto (T)", "Texto"),
            ("badge", "🔢 Passo (N)", "Passo"),
            ("crop", "✂️ Recortar (C)", "Recorte"),
        ]

        for tool_id, tool_label, tooltip in tool_specs:
            btn = ctk.CTkButton(
                tools_frame,
                text=tool_label,
                width=36,
                height=32,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#334155" if tool_id != self.current_tool else "#2563eb",
                hover_color="#1d4ed8",
                command=lambda tid=tool_id: self._select_tool(tid)
            )
            btn.pack(side="left", padx=2)
            self.tool_buttons[tool_id] = btn

        # Divisor
        ctk.CTkFrame(self.toolbar_frame, width=2, height=28, fg_color="#475569").pack(side="left", padx=8)

        # Seletor de Espessura
        width_frame = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        width_frame.pack(side="left", padx=2)

        self.width_buttons = {}
        for w_val, w_label in STROKE_WIDTHS:
            w_btn = ctk.CTkButton(
                width_frame,
                text=w_label,
                width=48,
                height=30,
                font=ctk.CTkFont(size=11),
                fg_color="#334155" if w_val != self.current_width else "#0284c7",
                hover_color="#0369a1",
                command=lambda val=w_val: self._select_width(val)
            )
            w_btn.pack(side="left", padx=2)
            self.width_buttons[w_val] = w_btn

        # Divisor
        ctk.CTkFrame(self.toolbar_frame, width=2, height=28, fg_color="#475569").pack(side="left", padx=8)

        # Paleta de Cores
        palette_frame = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        palette_frame.pack(side="left", padx=2)

        self.color_buttons = {}
        for hex_code, color_name in PALETTE_COLORS:
            # Botão circular ou quadrado para cada cor
            c_btn = ctk.CTkButton(
                palette_frame,
                text="",
                width=24,
                height=24,
                corner_radius=12,
                fg_color=hex_code,
                border_width=2 if hex_code == self.current_color else 0,
                border_color="#ffffff",
                hover_color=hex_code,
                command=lambda col=hex_code: self._select_color(col)
            )
            c_btn.pack(side="left", padx=3)
            self.color_buttons[hex_code] = c_btn

        # Histórico (Desfazer / Refazer / Limpar)
        hist_frame = ctk.CTkFrame(self.toolbar_frame, fg_color="transparent")
        hist_frame.pack(side="right", padx=8)

        self.btn_undo = ctk.CTkButton(
            hist_frame,
            text="↩️ Desfazer (Ctrl+Z)",
            width=80,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#475569",
            hover_color="#334155",
            command=self._action_undo
        )
        self.btn_undo.pack(side="left", padx=2)

        self.btn_redo = ctk.CTkButton(
            hist_frame,
            text="↪️ Refazer (Ctrl+Y)",
            width=80,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#475569",
            hover_color="#334155",
            command=self._action_redo
        )
        self.btn_redo.pack(side="left", padx=2)

        self.btn_clear = ctk.CTkButton(
            hist_frame,
            text="🗑️ Limpar",
            width=65,
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._action_clear_all
        )
        self.btn_clear.pack(side="left", padx=2)

    def _build_bottom_bar(self):
        bottom_frame = ctk.CTkFrame(self.main_container, fg_color="#1e293b", corner_radius=8)
        bottom_frame.pack(fill="x", pady=(4, 0), ipady=4)

        # Informações da captura e campo de texto
        info_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        info_row.pack(fill="x", padx=12, pady=(6, 4))

        win_title = self.metadata.get("window_title", "Janela Ativa")
        if len(win_title) > 65:
            win_title = win_title[:62] + "..."
        dim_info = f"{self.original_image.width}x{self.original_image.height} px"

        lbl_info = ctk.CTkLabel(
            info_row,
            text=f"📌 Chamado #{self.ticket_number}  |  {win_title} ({dim_info})",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray75"
        )
        lbl_info.pack(side="left")

        # Campo de Descrição
        desc_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        desc_row.pack(fill="x", padx=12, pady=(2, 6))

        self.entry_desc = ctk.CTkEntry(
            desc_row,
            placeholder_text="Descreva brevemente esta evidência (opcional, ex: clique no botão salvar, mensagem de alerta)...",
            height=36,
            font=ctk.CTkFont(size=13)
        )
        self.entry_desc.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_desc.bind("<Return>", lambda e: self._action_save())

        # Botão Copiar Imagem
        self.btn_copy = ctk.CTkButton(
            desc_row,
            text="📋 Copiar (Ctrl+C)",
            width=130,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._action_copy
        )
        self.btn_copy.pack(side="left", padx=(0, 8))

        # Botão Descartar
        self.btn_cancel = ctk.CTkButton(
            desc_row,
            text="Descartar (Esc)",
            width=110,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._action_cancel
        )
        self.btn_cancel.pack(side="left", padx=(0, 8))

        # Botão Salvar Evidência (Salva de verdade no chamado)
        self.btn_save = ctk.CTkButton(
            desc_row,
            text="💾 Salvar Evidência [Enter]",
            width=180,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            command=self._action_save
        )
        self.btn_save.pack(side="right")

    def _bind_events(self):
        # Redimensionamento dinâmico do canvas
        self.canvas.bind("<Configure>", lambda e: self._update_canvas_view())

        # Eventos do Mouse no Canvas
        self.canvas.bind("<Button-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Motion>", self._on_canvas_motion)

        # Atalhos Globais da Janela
        self.bind("<Escape>", lambda e: self._action_cancel())
        self.bind("<Control-s>", lambda e: self._action_save())
        self.bind("<Control-S>", lambda e: self._action_save())
        self.bind("<Control-z>", lambda e: self._action_undo())
        self.bind("<Control-Z>", lambda e: self._action_undo())
        self.bind("<Control-y>", lambda e: self._action_redo())
        self.bind("<Control-Y>", lambda e: self._action_redo())

        # Teclas de atalho para troca de ferramentas (quando o foco não estiver no entry)
        self.bind("<Key>", self._on_global_key)

        # Foco e protocolo de fechamento
        self.protocol("WM_DELETE_WINDOW", self._action_cancel)

    def _is_text_focused(self) -> bool:
        """Verifica se o cursor/foco do teclado está em um campo de digitação de texto."""
        focused = self.focus_get()
        if not focused:
            return False
        # Verifica se é o campo de descrição (CTkEntry ou seu _entry interno nativo)
        if hasattr(self, "entry_desc"):
            if focused == self.entry_desc or focused == getattr(self.entry_desc, "_entry", None):
                return True
        # Verifica se é o campo de anotação de texto inline no canvas
        if self.active_text_entry and (focused == self.active_text_entry or focused == getattr(self.active_text_entry, "_entry", None)):
            return True
        # Fallback para qualquer widget de entrada de texto nativo (Entry, Text)
        if isinstance(focused, (tk.Entry, tk.Text)):
            return True
        return False

    def _on_global_key(self, event):
        # Se estiver digitando no entry de descrição ou texto inline, NUNCA dispara ferramentas
        if self._is_text_focused():
            if event.keysym in ("Return", "KP_Enter"):
                # Se não for anotação de texto inline no canvas, salva o print
                if not self.active_text_entry:
                    self._action_save()
            return

        key = event.char.lower() if event.char else ""
        if key == "r":
            self._select_tool("rect")
        elif key == "a":
            self._select_tool("arrow")
        elif key == "p":
            self._select_tool("pen")
        elif key == "l":
            self._select_tool("line")
        elif key == "h":
            self._select_tool("highlight")
        elif key == "t":
            self._select_tool("text")
        elif key == "n":
            self._select_tool("badge")
        elif key == "c" and not (event.state & 0x4):  # 'c' sem Ctrl
            self._select_tool("crop")
        elif (event.state & 0x4) and key == "c":       # Ctrl+C
            self._action_copy()
        elif event.keysym in ("Return", "KP_Enter"):
            self._action_save()

    def _select_tool(self, tool_id: str):
        self._commit_active_text()
        self.current_tool = tool_id
        for tid, btn in self.tool_buttons.items():
            if tid == tool_id:
                btn.configure(fg_color="#2563eb")
            else:
                btn.configure(fg_color="#334155")

        # Ajusta cursor
        if tool_id == "text":
            self.canvas.configure(cursor="xterm")
        elif tool_id == "pen":
            self.canvas.configure(cursor="pencil")
        else:
            self.canvas.configure(cursor="crosshair")

    def _select_width(self, width_val: int):
        self.current_width = width_val
        for w_val, btn in self.width_buttons.items():
            if w_val == width_val:
                btn.configure(fg_color="#0284c7")
            else:
                btn.configure(fg_color="#334155")

    def _select_color(self, hex_color: str):
        self.current_color = hex_color
        for col_code, btn in self.color_buttons.items():
            if col_code == hex_color:
                btn.configure(border_width=2)
            else:
                btn.configure(border_width=0)

    # --- MAPEAMENTO DE COORDENADAS ---

    def _screen_to_image_coords(self, sx: float, sy: float) -> Tuple[float, float]:
        """Converte coordenadas da tela (Canvas) para pixels da imagem original."""
        ix = (sx - self.offset_x) / self.scale
        iy = (sy - self.offset_y) / self.scale
        # Limita aos limites da imagem
        ix = max(0.0, min(float(self.original_image.width), ix))
        iy = max(0.0, min(float(self.original_image.height), iy))
        return (ix, iy)

    def _image_to_screen_coords(self, ix: float, iy: float) -> Tuple[float, float]:
        """Converte pixels da imagem original para coordenadas da tela (Canvas)."""
        sx = (ix * self.scale) + self.offset_x
        sy = (iy * self.scale) + self.offset_y
        return (sx, sy)

    # --- DESENHO E ATUALIZAÇÃO DO CANVAS ---

    def _update_canvas_view(self):
        """Re-renderiza a imagem anotada com a escala atual do canvas."""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w <= 10 or canvas_h <= 10:
            return

        img_w, img_h = self.original_image.size

        # Calcula escala para caber suavemente sem distorção
        scale_x = canvas_w / img_w
        scale_y = canvas_h / img_h
        self.scale = min(scale_x, scale_y, 1.0)  # Evita upscaling excessivo

        display_w = max(1, int(img_w * self.scale))
        display_h = max(1, int(img_h * self.scale))

        self.offset_x = (canvas_w - display_w) // 2
        self.offset_y = (canvas_h - display_h) // 2

        # Gera a imagem renderizada com todas as anotações acumuladas
        rendered_pil = render_annotations(self.original_image, self.history, crop_box=self.crop_box)

        # Se houver crop_box aplicado, as dimensões da imagem mudam
        disp_img = rendered_pil.resize((display_w, display_h), Image.Resampling.LANCZOS)
        self.display_image_tk = ImageTk.PhotoImage(disp_img)

        self.canvas.delete("all")
        self.canvas.create_image(
            self.offset_x,
            self.offset_y,
            anchor="nw",
            image=self.display_image_tk,
            tags="background_image"
        )

        # Se houver recorte ativo, desenha moldura visual do recorte
        if self.crop_box:
            c_x1, c_y1, c_x2, c_y2 = self.crop_box
            sc_x1, sc_y1 = self._image_to_screen_coords(min(c_x1, c_x2), min(c_y1, c_y2))
            sc_x2, sc_y2 = self._image_to_screen_coords(max(c_x1, c_x2), max(c_y1, c_y2))
            self.canvas.create_rectangle(
                sc_x1, sc_y1, sc_x2, sc_y2,
                outline="#38bdf8",
                width=2,
                dash=(4, 4),
                tags="crop_guide"
            )

    # --- INTERAÇÃO COM MOUSE ---

    def _on_canvas_press(self, event):
        self._commit_active_text()
        img_x, img_y = self._screen_to_image_coords(event.x, event.y)

        # 1. Ferramenta de Texto: abre entrada inline
        if self.current_tool == "text":
            self._open_inline_text(event.x, event.y, (img_x, img_y))
            return

        # 2. Ferramenta de Passo Numérico: carimba imediatamente
        if self.current_tool == "badge":
            badge_action = AnnotationAction(
                kind="badge",
                points=[(img_x, img_y)],
                color=self.current_color,
                width=self.current_width,
                badge_number=self.badge_counter
            )
            self.badge_counter += 1
            self.history.append(badge_action)
            self.redo_stack.clear()
            self._update_canvas_view()
            return

        # Demais ferramentas iniciam arrasto
        self.is_dragging = True
        self.drag_start_img = (img_x, img_y)
        self.current_drag_points = [(img_x, img_y)]

        # Cria item temporário de preview no canvas
        sx, sy = event.x, event.y
        if self.current_tool in ("pen", "highlight"):
            # Linha acumulativa
            self.preview_item_id = self.canvas.create_line(
                sx, sy, sx, sy,
                fill=self.current_color,
                width=max(2, self.current_width if self.current_tool == "pen" else self.current_width * 3),
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                tags="preview"
            )
        elif self.current_tool == "line":
            self.preview_item_id = self.canvas.create_line(
                sx, sy, sx, sy,
                fill=self.current_color,
                width=max(2, self.current_width),
                tags="preview"
            )
        elif self.current_tool == "arrow":
            self.preview_item_id = self.canvas.create_line(
                sx, sy, sx, sy,
                fill=self.current_color,
                width=max(2, self.current_width),
                arrow=tk.LAST,
                arrowshape=(14, 18, 5),
                tags="preview"
            )
        elif self.current_tool == "rect":
            self.preview_item_id = self.canvas.create_rectangle(
                sx, sy, sx, sy,
                outline=self.current_color,
                width=max(2, self.current_width),
                tags="preview"
            )
        elif self.current_tool == "crop":
            self.preview_item_id = self.canvas.create_rectangle(
                sx, sy, sx, sy,
                outline="#38bdf8",
                width=2,
                dash=(5, 3),
                tags="preview"
            )

    def _on_canvas_drag(self, event):
        if not self.is_dragging or not self.drag_start_img:
            return

        img_x, img_y = self._screen_to_image_coords(event.x, event.y)
        sx, sy = event.x, event.y
        start_sx, start_sy = self._image_to_screen_coords(*self.drag_start_img)

        if self.current_tool in ("pen", "highlight"):
            self.current_drag_points.append((img_x, img_y))
            # Atualiza o traço do preview com todos os pontos convertidos
            screen_pts = []
            for px, py in self.current_drag_points:
                sc_x, sc_y = self._image_to_screen_coords(px, py)
                screen_pts.extend([sc_x, sc_y])
            if len(screen_pts) >= 4 and self.preview_item_id:
                self.canvas.coords(self.preview_item_id, *screen_pts)

        elif self.current_tool in ("line", "arrow", "rect", "crop"):
            if self.preview_item_id:
                self.canvas.coords(self.preview_item_id, start_sx, start_sy, sx, sy)

    def _on_canvas_release(self, event):
        if not self.is_dragging or not self.drag_start_img:
            return
        self.is_dragging = False

        img_end_x, img_end_y = self._screen_to_image_coords(event.x, event.y)
        start_x, start_y = self.drag_start_img

        # Remove preview temporário
        self.canvas.delete("preview")
        self.preview_item_id = None

        dx = abs(img_end_x - start_x)
        dy = abs(img_end_y - start_y)

        # Se for recorte
        if self.current_tool == "crop":
            if dx > 15 and dy > 15:
                x1, y1 = int(min(start_x, img_end_x)), int(min(start_y, img_end_y))
                x2, y2 = int(max(start_x, img_end_x)), int(max(start_y, img_end_y))
                self.crop_box = (x1, y1, x2, y2)
                # Volta para ferramenta retângulo por padrão após recortar
                self._select_tool("rect")
            self._update_canvas_view()
            return

        # Para ferramentas de desenho, ignora cliques minúsculos acidentais
        if self.current_tool not in ("pen", "highlight") and dx < 3 and dy < 3:
            return

        # Cria a ação correspondente
        action = None
        if self.current_tool == "pen":
            if len(self.current_drag_points) >= 2:
                action = AnnotationAction(
                    kind="pen",
                    points=list(self.current_drag_points),
                    color=self.current_color,
                    width=self.current_width
                )
        elif self.current_tool == "highlight":
            if len(self.current_drag_points) >= 2:
                action = AnnotationAction(
                    kind="highlight",
                    points=list(self.current_drag_points),
                    color=self.current_color,
                    width=self.current_width
                )
        elif self.current_tool == "line":
            action = AnnotationAction(
                kind="line",
                points=[(start_x, start_y), (img_end_x, img_end_y)],
                color=self.current_color,
                width=self.current_width
            )
        elif self.current_tool == "arrow":
            action = AnnotationAction(
                kind="arrow",
                points=[(start_x, start_y), (img_end_x, img_end_y)],
                color=self.current_color,
                width=self.current_width
            )
        elif self.current_tool == "rect":
            action = AnnotationAction(
                kind="rect",
                points=[(start_x, start_y), (img_end_x, img_end_y)],
                color=self.current_color,
                width=self.current_width
            )

        if action:
            self.history.append(action)
            self.redo_stack.clear()
            self._update_canvas_view()

    def _on_canvas_motion(self, event):
        pass

    # --- TEXTO INLINE ---

    def _open_inline_text(self, sx: float, sy: float, img_coords: Tuple[float, float]):
        self._commit_active_text()
        self.active_text_coords = img_coords

        entry_frame = tk.Frame(self.canvas, bg="#0f172a", bd=1, relief="solid")
        self.active_text_entry = tk.Entry(
            entry_frame,
            font=("Segoe UI", 12, "bold"),
            fg=self.current_color,
            bg="#0f172a",
            insertbackground="white",
            relief="flat"
        )
        self.active_text_entry.pack(padx=4, pady=2)
        self.active_text_entry.bind("<Return>", lambda e: self._commit_active_text())
        self.active_text_entry.bind("<Escape>", lambda e: self._cancel_active_text())

        # Posiciona no canvas
        self.canvas.create_window(sx, sy, anchor="nw", window=entry_frame, tags="text_input_window")
        self.active_text_entry.focus_set()

    def _commit_active_text(self):
        if not self.active_text_entry or not self.active_text_coords:
            return
        text_val = self.active_text_entry.get().strip()
        coords = self.active_text_coords

        self.canvas.delete("text_input_window")
        self.active_text_entry = None
        self.active_text_coords = None

        if text_val:
            action = AnnotationAction(
                kind="text",
                points=[coords],
                text=text_val,
                color=self.current_color,
                font_size=max(14, self.current_width * 5)
            )
            self.history.append(action)
            self.redo_stack.clear()
            self._update_canvas_view()

    def _cancel_active_text(self):
        self.canvas.delete("text_input_window")
        self.active_text_entry = None
        self.active_text_coords = None

    # --- HISTÓRICO: DESFAZER / REFAZER / LIMPAR ---

    def _action_undo(self):
        self._commit_active_text()
        if self.history:
            popped = self.history.pop()
            self.redo_stack.append(popped)
            # Se for badge, decrementa o contador
            if popped.kind == "badge" and self.badge_counter > 1:
                self.badge_counter -= 1
            self._update_canvas_view()
        elif self.crop_box:
            # Desfaz recorte se houver
            self.crop_box = None
            self._update_canvas_view()

    def _action_redo(self):
        self._commit_active_text()
        if self.redo_stack:
            restored = self.redo_stack.pop()
            self.history.append(restored)
            if restored.kind == "badge":
                self.badge_counter += 1
            self._update_canvas_view()

    def _action_clear_all(self):
        self._commit_active_text()
        if not self.history and not self.crop_box:
            return
        confirm = messagebox.askyesno(
            "Limpar Anotações",
            "Deseja remover todas as marcações e recortes deste print?",
            parent=self
        )
        if confirm:
            self.history.clear()
            self.redo_stack.clear()
            self.crop_box = None
            self.badge_counter = 1
            self._update_canvas_view()

    # --- AÇÕES FINAIS: COPIAR, SALVAR, CANCELAR ---

    def _get_final_rendered_image(self) -> Image.Image:
        """Gera a imagem final de alta resolução com todas as marcações e recorte."""
        self._commit_active_text()
        return render_annotations(self.original_image, self.history, crop_box=self.crop_box)

    def _action_copy(self):
        final_img = self._get_final_rendered_image()
        success = copy_image_to_clipboard(final_img)
        if success:
            orig_text = self.btn_copy.cget("text")
            self.btn_copy.configure(text="✅ Copiado!", fg_color="#16a34a")
            self.after(2000, lambda: self.btn_copy.configure(text=orig_text, fg_color="#0284c7"))

    def _action_save(self):
        """Salva a evidência definitivamente no chamado ativo."""
        if self.saved_or_cancelled:
            return
        self.saved_or_cancelled = True

        final_img = self._get_final_rendered_image()
        description = self.entry_desc.get().strip()

        self.destroy()
        if self.on_save_cb:
            self.on_save_cb(final_img, description)

    def _action_cancel(self):
        """Descarta a evidência capturada sem salvar nada no chamado."""
        if self.saved_or_cancelled:
            return
        self.saved_or_cancelled = True

        self.destroy()
        if self.on_cancel_cb:
            self.on_cancel_cb()

