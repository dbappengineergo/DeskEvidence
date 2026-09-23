import math
import io
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from PIL import Image, ImageDraw, ImageFont

try:
    import win32clipboard
    HAS_WIN32CLIPBOARD = True
except ImportError:
    HAS_WIN32CLIPBOARD = False


@dataclass
class AnnotationAction:
    """Representa uma ação individual de desenho/anotação na imagem."""
    kind: str  # 'pen', 'line', 'arrow', 'rect', 'highlight', 'text', 'badge'
    points: List[Tuple[float, float]] = field(default_factory=list)
    color: str = "#ef4444"  # Cor em hexadecimal
    width: int = 3          # Espessura do traço em pixels
    text: str = ""          # Texto da anotação (se kind == 'text')
    badge_number: int = 1   # Número sequencial (se kind == 'badge')
    font_size: int = 18     # Tamanho da fonte para texto ou badge


def hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """Converte uma cor hexadecimal (#RRGGBB ou #RGB) para tupla RGBA."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b, alpha)


def _get_font(font_size: int):
    """Tenta carregar uma fonte TrueType padrão do sistema Windows, com fallback seguro."""
    font_candidates = [
        "arial.ttf",
        "segoeui.ttf",
        "tahoma.ttf",
        "calibri.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf"
    ]
    for candidate in font_candidates:
        try:
            return ImageFont.truetype(candidate, size=font_size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    color: Tuple[int, int, int, int],
    width: int
):
    """Desenha uma seta indicativa estilizada com ponta triangular precisa."""
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    distance = math.hypot(dx, dy)
    if distance < 1:
        return

    # Ângulo da linha
    angle = math.atan2(dy, dx)
    # Tamanho da ponta proporcional à espessura
    arrow_size = max(14.0, width * 3.8)
    arrow_angle = math.radians(26)

    # Ponto onde a haste da seta termina (recuo leve para encaixar a ponta)
    stem_end_x = x2 - (arrow_size * 0.5) * math.cos(angle)
    stem_end_y = y2 - (arrow_size * 0.5) * math.sin(angle)

    # Desenha a linha principal
    draw.line([(x1, y1), (stem_end_x, stem_end_y)], fill=color, width=width)

    # Pontos da ponta triangular
    left_x = x2 - arrow_size * math.cos(angle - arrow_angle)
    left_y = y2 - arrow_size * math.sin(angle - arrow_angle)
    right_x = x2 - arrow_size * math.cos(angle + arrow_angle)
    right_y = y2 - arrow_size * math.sin(angle + arrow_angle)

    # Preenche a ponta da seta
    draw.polygon([(x2, y2), (left_x, left_y), (right_x, right_y)], fill=color)


def draw_badge(
    draw: ImageDraw.ImageDraw,
    center: Tuple[float, float],
    number: int,
    color: Tuple[int, int, int, int],
    radius: int = 15
):
    """Desenha um marcador circular numerado (Passo 1, 2, 3...) com sombra sutil."""
    cx, cy = center
    # Círculo externo com cor de destaque
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color, outline=(255, 255, 255, 230), width=2)

    # Texto centralizado em branco
    font = _get_font(int(radius * 1.15))
    text = str(number)
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = cx - tw / 2 - bbox[0]
        ty = cy - th / 2 - bbox[1]
    except Exception:
        tx = cx - 4
        ty = cy - 6

    draw.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)


def draw_text_annotation(
    draw: ImageDraw.ImageDraw,
    pos: Tuple[float, float],
    text: str,
    color: Tuple[int, int, int, int],
    font_size: int = 18
):
    """Desenha texto com fundo contrastante sutil para garantir legibilidade máxima."""
    if not text.strip():
        return
    x, y = pos
    font = _get_font(font_size)

    lines = text.split("\n")
    cur_y = y
    padding = 4

    for line in lines:
        try:
            bbox = draw.textbbox((x, cur_y), line, font=font)
            # Fundo suave escuro ou claro dependendo da cor do texto
            bg_rect = [bbox[0] - padding, bbox[1] - padding, bbox[2] + padding, bbox[3] + padding]
            # Desenha fundo semitransparente
            draw.rectangle(bg_rect, fill=(15, 23, 42, 210), outline=(255, 255, 255, 120), width=1)
            draw.text((x, cur_y), line, fill=color, font=font)
            line_height = (bbox[3] - bbox[1]) + padding * 2
        except Exception:
            draw.text((x, cur_y), line, fill=color, font=font)
            line_height = font_size + 6
        cur_y += line_height


def render_annotations(
    base_image: Image.Image,
    actions: List[AnnotationAction],
    crop_box: Optional[Tuple[int, int, int, int]] = None
) -> Image.Image:
    """
    Renderiza todas as ações de anotação sobre a imagem original em resolução 1:1.
    Retorna uma nova imagem PIL com as marcações aplicadas e o recorte (se definido).
    """
    # Trabalha sempre em modo RGBA para suporte a transparência em marca-texto
    working_image = base_image.convert("RGBA")

    # Camada transparente para overlays de marca-texto
    highlight_overlay = Image.new("RGBA", working_image.size, (0, 0, 0, 0))
    highlight_draw = ImageDraw.Draw(highlight_overlay)

    # Camada para anotações normais (opacas)
    overlay = Image.new("RGBA", working_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for action in actions:
        rgba = hex_to_rgba(action.color, 255)
        width = max(1, action.width)

        if action.kind == "pen":
            if len(action.points) >= 2:
                draw.line(action.points, fill=rgba, width=width, joint="curve")
            elif len(action.points) == 1:
                px, py = action.points[0]
                r = width / 2
                draw.ellipse([px - r, py - r, px + r, py + r], fill=rgba)

        elif action.kind == "line":
            if len(action.points) >= 2:
                draw.line([action.points[0], action.points[1]], fill=rgba, width=width)

        elif action.kind == "arrow":
            if len(action.points) >= 2:
                draw_arrow(draw, action.points[0], action.points[1], rgba, width)

        elif action.kind == "rect":
            if len(action.points) >= 2:
                p1, p2 = action.points[0], action.points[1]
                x1, y1 = min(p1[0], p2[0]), min(p1[1], p2[1])
                x2, y2 = max(p1[0], p2[0]), max(p1[1], p2[1])
                draw.rectangle([x1, y1, x2, y2], outline=rgba, width=width)

        elif action.kind == "highlight":
            # Marca-texto: traço semitransparente com alpha ~95 (aprox 37% de opacidade)
            hl_rgba = hex_to_rgba(action.color, 95)
            hl_width = max(18, width * 4)
            if len(action.points) >= 2:
                highlight_draw.line(action.points, fill=hl_rgba, width=hl_width, joint="curve")
            elif len(action.points) == 1:
                px, py = action.points[0]
                r = hl_width / 2
                highlight_draw.ellipse([px - r, py - r, px + r, py + r], fill=hl_rgba)

        elif action.kind == "text":
            if action.points and action.text:
                draw_text_annotation(draw, action.points[0], action.text, rgba, action.font_size)

        elif action.kind == "badge":
            if action.points:
                badge_radius = max(12, int(width * 2.8))
                draw_badge(draw, action.points[0], action.badge_number, rgba, radius=badge_radius)

    # Combina as camadas na ordem: base -> marca-texto -> anotações opacas
    working_image = Image.alpha_composite(working_image, highlight_overlay)
    working_image = Image.alpha_composite(working_image, overlay)

    final_image = working_image.convert("RGB")

    # Aplica o recorte final se houver
    if crop_box:
        x1, y1, x2, y2 = crop_box
        left = max(0, min(x1, x2))
        top = max(0, min(y1, y2))
        right = min(final_image.width, max(x1, x2))
        bottom = min(final_image.height, max(y1, y2))
        if right - left >= 10 and bottom - top >= 10:
            final_image = final_image.crop((left, top, right, bottom))

    return final_image


def copy_image_to_clipboard(image: Image.Image) -> bool:
    """Copia uma imagem PIL diretamente para a Área de Transferência (Clipboard) do Windows."""
    if not HAS_WIN32CLIPBOARD:
        return False

    try:
        output = io.BytesIO()
        image.convert("RGB").save(output, "BMP")
        # No formato CF_DIB do Windows, descartamos os primeiros 14 bytes do header BMP
        dib_data = output.getvalue()[14:]
        output.close()

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_data)
            return True
        finally:
            win32clipboard.CloseClipboard()
    except Exception as e:
        print(f"[AnnotationEngine] Falha ao copiar para clipboard: {e}")
        return False

