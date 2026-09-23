import os
import subprocess
from pathlib import Path
from typing import Optional, Callable
import customtkinter as ctk
from tkinter import messagebox

from deskevidence.core.ticket_manager import TicketManager

class TicketDialog(ctk.CTkToplevel):
    """
    Janela para criação de novo chamado, gerenciamento do chamado ativo
    ou troca entre chamados existentes.
    """

    def __init__(
        self,
        parent,
        ticket_manager: TicketManager,
        mode: str = "auto",  # 'auto', 'create', 'manage', 'switch'
        on_ticket_changed: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.ticket_mgr = ticket_manager
        self.on_ticket_changed = on_ticket_changed
        self.attributes("-topmost", True)
        self.resizable(False, False)

        active = self.ticket_mgr.get_active_ticket()

        if mode == "auto":
            if active:
                self.mode = "manage"
            else:
                self.mode = "create"
        else:
            self.mode = mode

        w, h = (520, 570) if self.mode == "manage" else (520, 480)
        self.geometry(f"{w}x{h}")
        self._center_window(w, h)

        self._render_view()

    def _center_window(self, width: int, height: int):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = int((screen_w - width) / 2)
        pos_y = int((screen_h - height) / 2)
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

    def _clear_view(self):
        for widget in self.winfo_children():
            widget.destroy()

    def _render_view(self):
        self._clear_view()
        if self.mode == "create":
            self._render_create_view()
        elif self.mode == "manage":
            self._render_manage_view()
        elif self.mode == "switch":
            self._render_switch_view()

    # --- TELA: NOVO CHAMADO ---
    def _render_create_view(self):
        self.title("DeskEvidence - Iniciar Novo Chamado / Projeto")

        main_frame = ctk.CTkFrame(self, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        lbl_title = ctk.CTkLabel(
            main_frame,
            text="Novo Chamado / Projeto",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(anchor="w", padx=16, pady=(16, 4))

        lbl_subtitle = ctk.CTkLabel(
            main_frame,
            text="Preencha os dados do trabalho a ser executado. O chamado ficará ativo.",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        lbl_subtitle.pack(anchor="w", padx=16, pady=(0, 16))

        # Número / Código
        ctk.CTkLabel(main_frame, text="Número / Identificador (ex: INC12345, REQ-890):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(4, 2))
        self.entry_number = ctk.CTkEntry(main_frame, placeholder_text="Digite o número do chamado...", height=36)
        self.entry_number.pack(fill="x", padx=16, pady=(0, 10))

        # Nome / Título
        ctk.CTkLabel(main_frame, text="Nome / Título do Chamado:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(4, 2))
        self.entry_name = ctk.CTkEntry(main_frame, placeholder_text="Ex: Validação de transmissão SPED / Erro de login...", height=36)
        self.entry_name.pack(fill="x", padx=16, pady=(0, 10))

        # Descrição inicial (opcional)
        ctk.CTkLabel(main_frame, text="Descrição Breve Inicial (opcional):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=16, pady=(4, 2))
        self.entry_desc = ctk.CTkTextbox(main_frame, height=80)
        self.entry_desc.pack(fill="x", padx=16, pady=(0, 16))

        # Botões
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(4, 12))

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            fg_color="#64748b",
            hover_color="#475569",
            width=100,
            command=self.destroy
        )
        btn_cancel.pack(side="left")

        # Se houver outros chamados, botão para alternar
        existing = self.ticket_mgr.list_tickets()
        if existing:
            btn_switch = ctk.CTkButton(
                btn_frame,
                text="Selecionar Existente",
                fg_color="#334155",
                hover_color="#1e293b",
                width=140,
                command=lambda: self._set_mode("switch")
            )
            btn_switch.pack(side="left", padx=(10, 0))

        btn_save = ctk.CTkButton(
            btn_frame,
            text="Criar e Ativar",
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(weight="bold"),
            command=self._do_create_ticket
        )
        btn_save.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Foco inicial
        self.after(100, lambda: self.entry_number.focus_set())

    def _save_current_conclusion(self) -> str:
        """Salva a conclusão digitada no chamado ativo caso esteja na tela de gerenciamento."""
        if hasattr(self, "txt_conclusion") and self.txt_conclusion:
            try:
                conclusion = self.txt_conclusion.get("1.0", "end-1c").strip()
                active = self.ticket_mgr.get_active_ticket()
                if active:
                    self.ticket_mgr.update_ticket_conclusion(active.get("id"), conclusion)
                return conclusion
            except Exception:
                pass
        return ""

    def _set_mode(self, mode: str):
        if getattr(self, "mode", None) == "manage":
            self._save_current_conclusion()
        self.mode = mode
        w, h = (520, 570) if self.mode == "manage" else (520, 480)
        self.geometry(f"{w}x{h}")
        self._render_view()

    def destroy(self):
        if getattr(self, "mode", None) == "manage":
            try:
                self._save_current_conclusion()
            except Exception:
                pass
        super().destroy()

    def _do_create_ticket(self):
        number = self.entry_number.get().strip()
        name = self.entry_name.get().strip()
        desc = self.entry_desc.get("1.0", "end").strip()

        if not number or not name:
            messagebox.showwarning(
                "Campos Obrigatórios",
                "Por favor, informe ao menos o Número e o Nome do Chamado.",
                parent=self
            )
            return

        self.ticket_mgr.create_ticket(number=number, name=name, description=desc)
        if self.on_ticket_changed:
            self.on_ticket_changed()
        self.destroy()

    # --- TELA: GERENCIAR CHAMADO ATIVO ---
    def _render_manage_view(self):
        self.title("DeskEvidence - Chamado Ativo")
        active = self.ticket_mgr.get_active_ticket()
        if not active:
            self._set_mode("create")
            return

        main_frame = ctk.CTkFrame(self, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Header status
        badge_frame = ctk.CTkFrame(main_frame, fg_color="#166534", corner_radius=6)
        badge_frame.pack(anchor="w", padx=16, pady=(16, 6))
        lbl_badge = ctk.CTkLabel(badge_frame, text="● CHAMADO ATIVO NO MOMENTO", font=ctk.CTkFont(size=11, weight="bold"), text_color="#bbf7d0")
        lbl_badge.pack(padx=10, pady=3)

        lbl_title = ctk.CTkLabel(
            main_frame,
            text=f"#{active.get('number')} - {active.get('name')}",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(anchor="w", padx=16, pady=(4, 2))

        lbl_desc = ctk.CTkLabel(
            main_frame,
            text=active.get('description') or "Sem descrição adicional informada.",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
            wraplength=460,
            justify="left"
        )
        lbl_desc.pack(anchor="w", padx=16, pady=(0, 16))

        # Estatísticas do chamado ativo
        stats_frame = ctk.CTkFrame(main_frame, fg_color="#1e293b", corner_radius=8)
        stats_frame.pack(fill="x", padx=16, pady=(0, 16))

        num_evidencias = len(active.get("evidences", []))
        lbl_stat1 = ctk.CTkLabel(
            stats_frame,
            text=f"📸 Evidências Capturadas: {num_evidencias}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_stat1.pack(anchor="w", padx=14, pady=(10, 2))

        lbl_stat2 = ctk.CTkLabel(
            stats_frame,
            text=f"Iniciado em: {active.get('created_at_display', '')}",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        lbl_stat2.pack(anchor="w", padx=14, pady=(0, 10))

        # Ações do chamado
        btn_open_folder = ctk.CTkButton(
            main_frame,
            text="Abrir Pasta das Evidências no Explorer",
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            command=lambda: self._open_folder(active.get("folder_path"))
        )
        btn_open_folder.pack(fill="x", padx=16, pady=(0, 8))

        # Campo para conclusão textual do chamado
        lbl_conclusion = ctk.CTkLabel(
            main_frame,
            text="Conclusão / Parecer Técnico:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray85"
        )
        lbl_conclusion.pack(anchor="w", padx=16, pady=(4, 2))

        self.txt_conclusion = ctk.CTkTextbox(
            main_frame,
            height=70,
            corner_radius=6,
            font=ctk.CTkFont(size=12)
        )
        self.txt_conclusion.pack(fill="x", padx=16, pady=(0, 8))

        # Pré-carrega conclusão existente se houver
        existing_conclusion = active.get("conclusion", "")
        if existing_conclusion:
            self.txt_conclusion.insert("1.0", existing_conclusion)

        btn_finish = ctk.CTkButton(
            main_frame,
            text="🏁 Finalizar Chamado e Gerar Relatório HTML",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold"),
            height=38,
            command=self._do_finish_active
        )
        btn_finish.pack(fill="x", padx=16, pady=(0, 8))

        # Linha de Exportação Direta (PDF e Word)
        export_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        export_frame.pack(fill="x", padx=16, pady=(0, 8))

        btn_export_pdf = ctk.CTkButton(
            export_frame,
            text="Salvar em PDF / Imprimir",
            fg_color="#b91c1c",
            hover_color="#991b1b",
            font=ctk.CTkFont(weight="bold"),
            height=36,
            command=self._do_export_pdf
        )
        btn_export_pdf.pack(side="left", fill="x", expand=True, padx=(0, 4))

        btn_export_word = ctk.CTkButton(
            export_frame,
            text="Salvar em Word (.doc)",
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(weight="bold"),
            height=36,
            command=self._do_export_word
        )
        btn_export_word.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Barra inferior de opções extras
        extra_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        extra_frame.pack(fill="x", padx=16, pady=(8, 12))

        btn_switch = ctk.CTkButton(
            extra_frame,
            text="Trocar Chamado...",
            fg_color="#475569",
            hover_color="#334155",
            width=130,
            command=lambda: self._set_mode("switch")
        )
        btn_switch.pack(side="left")

        btn_new = ctk.CTkButton(
            extra_frame,
            text="Novo Chamado...",
            fg_color="#475569",
            hover_color="#334155",
            width=130,
            command=lambda: self._set_mode("create")
        )
        btn_new.pack(side="left", padx=(8, 0))

        btn_close = ctk.CTkButton(
            extra_frame,
            text="Fechar",
            fg_color="#64748b",
            hover_color="#475569",
            width=80,
            command=self.destroy
        )
        btn_close.pack(side="right")

    def _open_folder(self, folder_path: Optional[str]):
        if folder_path and Path(folder_path).exists():
            os.startfile(folder_path)

    def _do_finish_active(self):
        active = self.ticket_mgr.get_active_ticket()
        if not active:
            return

        confirm = messagebox.askyesno(
            "Finalizar Chamado",
            f"Deseja finalizar o chamado #{active.get('number')}?\nUm relatório HTML consolidado será gerado automaticamente.",
            parent=self
        )
        if not confirm:
            return

        conclusion = self._save_current_conclusion()
        ticket, report_path = self.ticket_mgr.finish_active_ticket(conclusion=conclusion)
        if self.on_ticket_changed:
            self.on_ticket_changed()

        messagebox.showinfo(
            "Chamado Finalizado",
            f"Chamado finalizado com sucesso!\nRelatório gerado em:\n{report_path}",
            parent=self
        )

        # Abre o relatório HTML diretamente no navegador
        if report_path and Path(report_path).exists():
            os.startfile(report_path)

        self.destroy()

    def _do_export_pdf(self):
        self._save_current_conclusion()
        active = self.ticket_mgr.get_active_ticket()
        if not active:
            return
        try:
            html_path, _ = self.ticket_mgr.export_reports(active)
            if html_path and Path(html_path).exists():
                os.startfile(html_path)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar PDF", f"Falha ao gerar relatório: {e}", parent=self)

    def _do_export_word(self):
        self._save_current_conclusion()
        active = self.ticket_mgr.get_active_ticket()
        if not active:
            return
        try:
            _, doc_path = self.ticket_mgr.export_reports(active)
            if doc_path and Path(doc_path).exists():
                os.startfile(doc_path)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar Word", f"Falha ao gerar documento Word: {e}", parent=self)

    # --- TELA: SELECIONAR / TROCAR CHAMADO ---
    def _render_switch_view(self):
        self.title("DeskEvidence - Selecionar / Trocar Chamado")

        main_frame = ctk.CTkFrame(self, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        lbl_title = ctk.CTkLabel(
            main_frame,
            text="Histórico de Chamados e Projetos",
            font=ctk.CTkFont(size=17, weight="bold")
        )
        lbl_title.pack(anchor="w", padx=16, pady=(16, 4))

        tickets = self.ticket_mgr.list_tickets()

        scroll_frame = ctk.CTkScrollableFrame(main_frame, height=260)
        scroll_frame.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        if not tickets:
            ctk.CTkLabel(scroll_frame, text="Nenhum chamado encontrado na pasta padrão.", text_color="gray70").pack(pady=40)
        else:
            for t in tickets:
                t_id = t.get("id")
                is_active = self.ticket_mgr.get_active_ticket() and self.ticket_mgr.get_active_ticket().get("id") == t_id
                status = t.get("status", "active")

                card = ctk.CTkFrame(scroll_frame, fg_color="#1e293b" if not is_active else "#14532d", corner_radius=8)
                card.pack(fill="x", pady=4, padx=2)

                top_row = ctk.CTkFrame(card, fg_color="transparent")
                top_row.pack(fill="x", padx=10, pady=(6, 2))

                prefix = "● [ATIVO] " if is_active else ""
                suffix = " (Finalizado)" if status == "completed" else ""
                lbl_tname = ctk.CTkLabel(
                    top_row,
                    text=f"{prefix}#{t.get('number')} - {t.get('name')}{suffix}",
                    font=ctk.CTkFont(weight="bold", size=13),
                    anchor="w"
                )
                lbl_tname.pack(side="left", fill="x", expand=True)

                lbl_count = ctk.CTkLabel(
                    top_row,
                    text=f"{len(t.get('evidences', []))} fotos",
                    text_color="gray70",
                    font=ctk.CTkFont(size=11)
                )
                lbl_count.pack(side="right")

                btn_row = ctk.CTkFrame(card, fg_color="transparent")
                btn_row.pack(fill="x", padx=10, pady=(2, 6))

                if not is_active:
                    btn_activate = ctk.CTkButton(
                        btn_row,
                        text="Tornar Ativo",
                        height=26,
                        width=90,
                        fg_color="#16a34a",
                        hover_color="#15803d",
                        command=lambda tid=t_id: self._do_switch_to(tid)
                    )
                    btn_activate.pack(side="left")

                btn_open = ctk.CTkButton(
                    btn_row,
                    text="Abrir Pasta",
                    height=26,
                    width=85,
                    fg_color="#334155",
                    hover_color="#475569",
                    command=lambda f=t.get("folder_path"): self._open_folder(f)
                )
                btn_open.pack(side="left", padx=(6, 0))

        # Rodapé
        btn_footer = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_footer.pack(fill="x", padx=16, pady=(4, 10))

        btn_new = ctk.CTkButton(
            btn_footer,
            text="+ Novo Chamado",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            width=130,
            command=lambda: self._set_mode("create")
        )
        btn_new.pack(side="left")

        btn_close = ctk.CTkButton(
            btn_footer,
            text="Voltar / Fechar",
            fg_color="#64748b",
            hover_color="#475569",
            width=110,
            command=self.destroy
        )
        btn_close.pack(side="right")

    def _do_switch_to(self, ticket_id: str):
        self.ticket_mgr.set_active_ticket(ticket_id)
        if self.on_ticket_changed:
            self.on_ticket_changed()
        self.destroy()
