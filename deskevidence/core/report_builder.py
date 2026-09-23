import base64
import html
from pathlib import Path
from typing import Dict, Any, List, Optional


def _build_word_xml_template(ticket_data: Dict[str, Any], content_html: str) -> str:
    """Gera o template de documento compatível com Microsoft Word (.doc) baseado em MHTML/HTML."""
    ticket_num = ticket_data.get("number", "S/N")
    ticket_name = ticket_data.get("name", "Sem Título")

    return f"""<!DOCTYPE html>
<html xmlns:o='urn:schemas-microsoft-com:office:office' 
      xmlns:w='urn:schemas-microsoft-com:office:word' 
      xmlns='http://www.w3.org/TR/REC-html40'>
<head>
    <meta charset='utf-8'>
    <title>Relatório de Evidências - {ticket_num} {ticket_name}</title>
    <!--[if gte mso 9]>
    <xml>
        <w:WordDocument>
            <w:View>Print</w:View>
            <w:Zoom>100</w:Zoom>
            <w:DoNotOptimizeForBrowser/>
        </w:WordDocument>
    </xml>
    <![endif]-->
    <style>
        @page {{
            size: A4 portrait;
            margin: 2cm 2cm 2cm 2cm;
            mso-header-margin: 1cm;
            mso-footer-margin: 1cm;
        }}
        body {{
            font-family: 'Segoe UI', Calibri, Arial, sans-serif;
            font-size: 11pt;
            color: #0f172a;
            line-height: 1.5;
            margin: 0;
            padding: 0;
        }}
        .header {{
            background-color: #16223f;
            color: #ffffff;
            padding: 20px;
            margin-bottom: 24px;
            border-radius: 6px;
        }}
        .logo-space {{
            text-align: right;
            margin-bottom: 10px;
        }}
        .logo-space img {{
            max-height: 42px;
            max-width: 180px;
        }}
        .logo-placeholder {{
            color: #9db3d1;
            font-size: 8.5pt;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        .ticket-number {{
            color: #7fd490;
            font-size: 13pt;
            font-weight: bold;
        }}
        .status-badge {{
            background-color: #eef2f7;
            color: #1e293b;
            padding: 4px 10px;
            font-size: 9pt;
            font-weight: bold;
            border-radius: 12px;
            border: 1px solid #dbe3ec;
        }}
        .ticket-title {{
            font-size: 20pt;
            font-weight: bold;
            margin: 8px 0;
            color: #ffffff;
        }}
        .ticket-desc {{
            color: #cbd5e1;
            font-size: 11pt;
            margin-bottom: 16px;
        }}
        .meta-table {{
            width: 100%;
            border-top: 1px solid #475569;
            margin-top: 14px;
            padding-top: 10px;
        }}
        .meta-table td {{
            padding: 4px 8px;
            font-size: 9.5pt;
            color: #f1f5f9;
        }}
        .meta-table td strong {{
            color: #94a3b8;
            font-size: 8pt;
            text-transform: uppercase;
            display: block;
        }}
        .section-title {{
            font-size: 14pt;
            font-weight: bold;
            color: #1e293b;
            margin: 28px 0 16px 0;
            border-bottom: 2px solid #3f9152;
            padding-bottom: 6px;
        }}
        .evidence-card {{
            border: 1px solid #dde3ea;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 24px;
            page-break-inside: avoid;
            break-inside: avoid;
            background-color: #ffffff;
        }}
        .card-header {{
            border-bottom: 1px solid #eef1f5;
            padding-bottom: 8px;
            margin-bottom: 10px;
        }}
        .badge-index {{
            background-color: #e6f0e9;
            color: #245c37;
            font-weight: bold;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 9.5pt;
        }}
        .evidence-time {{
            color: #64748b;
            font-size: 9.5pt;
            margin-left: 10px;
        }}
        .badge-process {{
            background-color: #eef1f5;
            color: #475569;
            font-family: Consolas, monospace;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 9pt;
        }}
        .card-title {{
            font-size: 11pt;
            color: #1e293b;
            margin: 8px 0;
        }}
        .card-notes {{
            background-color: #f4f8f5;
            border-left: 4px solid #3f9152;
            padding: 10px 14px;
            margin: 12px 0;
            font-size: 10pt;
        }}
        .card-notes p {{
            margin-top: 4px;
            color: #334155;
        }}
        .card-image-wrap {{
            text-align: center;
            margin-top: 14px;
            background-color: #f7f9fb;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 6px;
        }}
        .card-image-wrap img {{
            max-width: 100%;
            height: auto;
            max-height: 520px;
        }}
        .footer {{
            text-align: center;
            font-size: 9pt;
            color: #64748b;
            margin-top: 36px;
            border-top: 1px solid #e2e8f0;
            padding-top: 16px;
        }}
    </style>
</head>
<body>
    {content_html}
</body>
</html>
"""


def generate_html_report(ticket_data: Dict[str, Any], output_path: Path, embed_images_as_base64: bool = True) -> str:
    """
    Gera um relatório HTML completo, profissional e interativo com botões
    integrados para Salvar em PDF e Salvar em Word (.doc).
    """
    evidences: List[Dict[str, Any]] = ticket_data.get("evidences", [])
    ticket_num = ticket_data.get("number", "S/N")
    ticket_name = ticket_data.get("name", "Sem Título")
    
    # Processa cada evidência para o HTML
    evidence_items_html = []
    for idx, ev in enumerate(evidences, 1):
        rel_path = ev.get("relative_path", "")
        img_src = rel_path.replace("\\", "/")
        
        # Se configurado para embutir base64 (arquivo 100% autônomo e compatível com exportação Word)
        if embed_images_as_base64:
            img_full = output_path.parent / rel_path
            if not img_full.exists():
                img_full = Path(rel_path)
            if img_full.exists():
                try:
                    with open(img_full, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        img_src = f"data:image/png;base64,{b64}"
                except Exception:
                    pass

        description = ev.get("description", "").strip()
        if not description:
            description = "<em style='color: #888;'>Nenhuma descrição adicional informada.</em>"

        item_html = f"""
        <div class="evidence-card">
            <div class="card-notes">
                <strong>Descrição da Ação:</strong>
                <p>{description}</p>
            </div>
            <div class="card-image-wrap">
                <a href="{img_src}" target="_blank" title="Clique para abrir imagem em tamanho real">
                    <img src="{img_src}" alt="Evidência #{idx}" loading="lazy" />
                </a>
            </div>
        </div>
        """
        evidence_items_html.append(item_html)

    cards_rendered = "\n".join(evidence_items_html) if evidence_items_html else """
        <div class="no-evidence">
            <p>Nenhuma evidência capturada para este chamado.</p>
        </div>
    """

    status_badge_class = "status-completed" if ticket_data.get("status") == "completed" else "status-active"
    status_label = "Finalizado" if ticket_data.get("status") == "completed" else "Em Andamento"

    # Espaço reservado para a marca/logotipo da empresa no cabeçalho.
    # Se `ticket_data['company_logo_base64']` (ou `company_logo_path`) for informado, o logo é exibido;
    # caso contrário, mantém-se um espaço reservado discreto.
    logo_b64 = ticket_data.get("company_logo_base64", "")
    logo_path = ticket_data.get("company_logo_path", "")
    if not logo_b64 and logo_path:
        logo_file = Path(logo_path)
        if logo_file.exists():
            try:
                with open(logo_file, "rb") as f:
                    ext = logo_file.suffix.lstrip(".") or "png"
                    logo_b64 = f"data:image/{ext};base64,{base64.b64encode(f.read()).decode('utf-8')}"
            except Exception:
                logo_b64 = ""

    if logo_b64:
        logo_html = f'<img src="{logo_b64}" alt="{ticket_data.get("company_name", "Logotipo da empresa")}" />'
    else:
        company_name = ticket_data.get("company_name", "Logotipo da empresa")
        logo_html = f'<span class="logo-placeholder">{html.escape(company_name)}</span>'

    company_address = ticket_data.get("company_address", "")

    # Bloco de Conclusão / Parecer Técnico
    conclusion_text = ticket_data.get("conclusion", "").strip()
    if conclusion_text:
        escaped_conclusion = html.escape(conclusion_text).replace("\n", "<br>")
        conclusion_body = f'<div class="conclusion-body">{escaped_conclusion}</div>'
    else:
        conclusion_body = '<div class="conclusion-body empty">Nenhuma conclusão ou parecer técnico informado.</div>'

    conclusion_html = f"""
        <div class="conclusion-card">
            <div class="conclusion-header">
                <h3 class="conclusion-title">Conclusão / Parecer Técnico</h3>
            </div>
            {conclusion_body}
        </div>
    """

    # Conteúdo principal do relatório (compartilhado entre visualização web e exportações)
    body_content_html = f"""
        <header class="header">
            <div class="logo-row">
                {logo_html}
            </div>
            <div class="header-top">
                <span class="ticket-number">Chamado #{ticket_num}</span>
                <span class="status-badge {status_badge_class}">{status_label}</span>
            </div>
            <h1 class="ticket-title">{ticket_name}</h1>
            <p class="ticket-desc">{ticket_data.get('description', 'Sem descrição.')}</p>
            
            <div class="meta-grid">
                <div class="meta-item">
                    <strong>Criado em:</strong>
                    <span>{ticket_data.get('created_at_display', ticket_data.get('created_at', ''))}</span>
                </div>
                <div class="meta-item">
                    <strong>Finalizado em:</strong>
                    <span>{ticket_data.get('closed_at_display', ticket_data.get('closed_at', 'Em andamento'))}</span>
                </div>
                <div class="meta-item">
                    <strong>Total de Evidências:</strong>
                    <span>{len(evidences)} captura(s)</span>
                </div>
            </div>
        </header>

        <h2 class="section-title">Registro da Evidências</h2>
        {cards_rendered}

        {conclusion_html}
    """

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Evidências - {ticket_num} {ticket_name}</title>
    <style>
        :root {{
            --primary: #1b2a4b;
            --primary-light: #3f9152;
            --bg: #f4f6f9;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --success: #3f9152;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text-main); line-height: 1.5; padding: 24px; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        
        /* BARRA SUPERIOR DE AÇÕES (PDF E WORD) */
        .action-bar {{
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            padding: 14px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            position: sticky;
            top: 12px;
            z-index: 100;
        }}
        .action-bar-info {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.95rem;
            color: #334155;
            font-weight: 600;
        }}
        .action-buttons {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 9px 18px;
            border-radius: 8px;
            font-size: 0.92rem;
            font-weight: 600;
            cursor: pointer;
            border: none;
            transition: all 0.2s ease;
            text-decoration: none;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
        }}
        .btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.12);
        }}
        .btn:active {{
            transform: translateY(0);
        }}
        .btn-pdf {{
            background-color: #1b2a4b;
            color: #ffffff;
        }}
        .btn-pdf:hover {{
            background-color: #142038;
        }}
        .btn-word {{
            background-color: #2f7a44;
            color: #ffffff;
        }}
        .btn-word:hover {{
            background-color: #246035;
        }}
        .btn svg {{
            width: 18px;
            height: 18px;
            fill: currentColor;
        }}

        .header {{
            background: linear-gradient(135deg, #1b2a4b 0%, #142038 100%);
            color: #ffffff;
            padding: 32px;
            border-radius: 8px;
            margin-bottom: 24px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
        }}
        .logo-row {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            margin-bottom: 18px;
            min-height: 32px;
        }}
        .logo-row img {{
            max-height: 40px;
            max-width: 200px;
            object-fit: contain;
        }}
        .logo-placeholder {{
            color: #9fb4d1;
            font-size: 0.75rem;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            border: 1px dashed #3a4d70;
            padding: 6px 14px;
            border-radius: 4px;
        }}
        .header-top {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
        .ticket-number {{ font-size: 1.25rem; font-weight: 700; color: #7fd490; letter-spacing: 0.5px; }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            background: #eef2f7;
            color: #1e293b;
        }}
        .status-badge::before {{
            content: '';
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }}
        .status-completed::before {{ background: #22c55e; }}
        .status-active::before {{ background: #f59e0b; }}
        
        .ticket-title {{ font-size: 2rem; font-weight: 700; margin-bottom: 12px; }}
        .ticket-desc {{ font-size: 1.05rem; color: #cbd8ea; margin-bottom: 20px; }}
        
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            padding-top: 16px;
            border-top: 1px solid #2c3e5c;
            font-size: 0.9rem;
        }}
        .meta-item strong {{ color: #9fb4d1; display: block; font-size: 0.75rem; text-transform: uppercase; }}
        
        .section-title {{
            font-size: 1.4rem;
            font-weight: 700;
            color: #1e293b;
            margin: 32px 0 16px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .evidence-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            break-inside: avoid;
            page-break-inside: avoid;
        }}
        .card-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eef1f5;
        }}
        .badge-index {{
            background: #e6f0e9;
            color: #245c37;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.9rem;
        }}
        .evidence-time {{ color: var(--text-muted); font-size: 0.9rem; }}
        .badge-process {{
            margin-left: auto;
            background: #eef1f5;
            color: #475569;
            font-family: monospace;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.85rem;
        }}
        .card-title {{ font-size: 1.05rem; color: #1e293b; margin-bottom: 8px; }}
        .card-notes {{
            background: #f4f8f5;
            border-left: 4px solid var(--primary-light);
            padding: 12px;
            border-radius: 0 6px 6px 0;
            margin-bottom: 16px;
            font-size: 0.95rem;
        }}
        .card-notes p {{ margin-top: 4px; color: #334155; }}
        
        .card-image-wrap {{
            text-align: center;
            background: #f7f9fb;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 10px;
            overflow: hidden;
        }}
        .card-image-wrap img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            display: block;
            margin: 0 auto;
            max-height: 600px;
            object-fit: contain;
        }}
        
        /* BLOCO DE CONCLUSÃO DO CHAMADO */
        .conclusion-card {{
            background: var(--card-bg);
            border: 1px solid #dde3ea;
            border-left: 6px solid #3f9152;
            border-radius: 8px;
            padding: 24px;
            margin-top: 32px;
            margin-bottom: 32px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            break-inside: avoid;
            page-break-inside: avoid;
        }}
        .conclusion-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 14px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eef1f5;
        }}
        .conclusion-icon {{
            font-size: 1.5rem;
        }}
        .conclusion-title {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #1b2a4b;
            margin: 0;
        }}
        .conclusion-body {{
            font-size: 1.05rem;
            line-height: 1.6;
            color: #1e293b;
        }}
        .conclusion-body.empty {{
            color: #94a3b8;
            font-style: italic;
        }}

        .footer-address {{
            text-align: center;
            padding-top: 18px;
            margin-top: 8px;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.8rem;
            line-height: 1.5;
        }}

        .footer {{
            text-align: center;
            padding: 24px;
            color: var(--text-muted);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            margin-top: 40px;
        }}

        /* ESTILOS DE IMPRESSÃO / SALVAR EM PDF */
        @media print {{
            @page {{
                margin: 1.5cm;
                size: A4 portrait;
            }}
            body {{
                background: #ffffff !important;
                color: #000000 !important;
                padding: 0 !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            .no-print {{
                display: none !important;
            }}
            .header {{
                background: #16223f !important;
                color: #ffffff !important;
                box-shadow: none !important;
                border: 1px solid #24406b !important;
                page-break-after: avoid;
            }}
            .evidence-card {{
                box-shadow: none !important;
                border: 1px solid #dde3ea !important;
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                margin-bottom: 20px !important;
            }}
            .conclusion-card {{
                box-shadow: none !important;
                border: 1px solid #3f9152 !important;
                border-left: 6px solid #3f9152 !important;
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                margin-top: 24px !important;
                margin-bottom: 24px !important;
            }}
            .card-image-wrap {{
                background: #ffffff !important;
                border: 1px solid #e2e8f0 !important;
                padding: 4px !important;
            }}
            .card-image-wrap img {{
                max-height: 480px !important;
                page-break-inside: avoid !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- BARRA DE AÇÕES (PDF / WORD) -->
        <div class="action-bar no-print">
            <div class="action-bar-info">
                <span>Opções de Exportação do Relatório:</span>
            </div>
            <div class="action-buttons">
                <button id="btn-pdf" class="btn btn-pdf" onclick="window.print()" title="Salvar relatório como PDF ou Imprimir">
                    <svg viewBox="0 0 24 24"><path d="M19 8H5c-1.66 0-3 1.34-3 3v6h4v4h12v-4h4v-6c0-1.66-1.34-3-3-3zm-3 11H8v-5h8v5zm3-7c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm-1-9H6v4h12V3z"/></svg>
                    Salvar em PDF / Imprimir
                </button>
                <button id="btn-word" class="btn btn-word" onclick="exportToWord()" title="Exportar e baixar como documento do Word (.doc)">
                    <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                    Salvar em Word (.doc)
                </button>
            </div>
        </div>

        <div id="report-content">
            {body_content_html}
        </div>
    </div>
</body>
</html>
"""
    output_path.write_text(html_content, encoding="utf-8")
    return str(output_path)


def generate_word_report(ticket_data: Dict[str, Any], output_path: Path) -> str:
    """
    Gera diretamente um documento do Word (.doc) auto-suficiente com todas as
    evidências embutidas em base64.
    """
    evidences: List[Dict[str, Any]] = ticket_data.get("evidences", [])
    ticket_num = ticket_data.get("number", "S/N")
    ticket_name = ticket_data.get("name", "Sem Título")

    evidence_items_html = []
    for idx, ev in enumerate(evidences, 1):
        rel_path = ev.get("relative_path", "")
        img_src = rel_path.replace("\\", "/")

        img_full = output_path.parent / rel_path
        if not img_full.exists():
            img_full = Path(rel_path)
        if img_full.exists():
            try:
                with open(img_full, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    img_src = f"data:image/png;base64,{b64}"
            except Exception:
                pass

        description = ev.get("description", "").strip()
        if not description:
            description = "<em style='color: #888;'>Nenhuma descrição informada.</em>"

        item_html = f"""
        <div class="evidence-card">
            <div class="card-notes">
                <strong>Descrição da Ação:</strong>
                <p>{description}</p>
            </div>
            <div class="card-image-wrap">
                <img src="{img_src}" alt="Evidência #{idx}" />
            </div>
        </div>
        """
        evidence_items_html.append(item_html)

    cards_rendered = "\n".join(evidence_items_html) if evidence_items_html else "<p>Nenhuma evidência registrada.</p>"
    status_label = "Finalizado" if ticket_data.get("status") == "completed" else "Em Andamento"

    # Espaço reservado para a marca/logotipo da empresa (mesma lógica da versão HTML).
    logo_b64 = ticket_data.get("company_logo_base64", "")
    logo_path = ticket_data.get("company_logo_path", "")
    if not logo_b64 and logo_path:
        logo_file = Path(logo_path)
        if logo_file.exists():
            try:
                with open(logo_file, "rb") as f:
                    ext = logo_file.suffix.lstrip(".") or "png"
                    logo_b64 = f"data:image/{ext};base64,{base64.b64encode(f.read()).decode('utf-8')}"
            except Exception:
                logo_b64 = ""

    if logo_b64:
        logo_html = f'<img src="{logo_b64}" alt="{ticket_data.get("company_name", "Logotipo da empresa")}" />'
    else:
        company_name = ticket_data.get("company_name", "Logotipo da empresa")
        logo_html = f'<span class="logo-placeholder">{html.escape(company_name)}</span>'

    company_address = ticket_data.get(
        "company_address",
        "Avenida T1, 2266, Edifício Alpha, 2º e 3º andares, Setor Bueno, 74.215-022<br>Goiânia – Goiás",
    )

    conclusion_text = ticket_data.get("conclusion", "").strip()
    if conclusion_text:
        escaped_conclusion = html.escape(conclusion_text).replace("\n", "<br>")
        conclusion_word_html = f"""
        <div style="border: 2px solid #2563eb; border-left: 6px solid #2563eb; padding: 16px; margin-top: 24px; margin-bottom: 24px; background-color: #f8fafc;">
            <h3 style="color: #1e3a8a; margin-top: 0; margin-bottom: 10px;">Conclusão / Parecer Técnico:</h3>
            <p style="font-size: 11pt; line-height: 1.5; color: #1e293b; margin: 0;">{escaped_conclusion}</p>
        </div>
        """
    else:
        conclusion_word_html = """
        <div style="border: 1px solid #cbd5e1; border-left: 4px solid #94a3b8; padding: 12px; margin-top: 20px; margin-bottom: 20px; background-color: #f8fafc;">
            <h3 style="color: #475569; margin-top: 0; margin-bottom: 6px;">Conclusão / Parecer Técnico:</h3>
            <p style="font-size: 10pt; color: #64748b; font-style: italic; margin: 0;">Nenhuma conclusão informada.</p>
        </div>
        """

    body_html = f"""
        <div class="header">
            <div class="logo-space">
                {logo_html}
            </div>
            <div>
                <span class="ticket-number">Chamado - {ticket_num}</span>
                <span class="status-badge">{status_label}</span>
            </div>
            <h1 class="ticket-title">{ticket_name}</h1>
            <p class="ticket-desc">{ticket_data.get('description', '')}</p>
            <table class="meta-table">
                <tr>
                    <td><strong>Evidências:</strong> {len(evidences)} captura(s)</td>
                </tr>
            </table>
        </div>

        <h2 class="section-title">Registro Cronológico de Evidências</h2>
        {cards_rendered}

        {conclusion_word_html}

        <div class="footer">{company_address}</div>
    """

    doc_content = _build_word_xml_template(ticket_data, body_html)
    output_path.write_text(doc_content, encoding="utf-8")
    return str(output_path)
