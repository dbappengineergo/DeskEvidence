from pathlib import Path
from PIL import Image, ImageDraw

def create_app_icon(is_active: bool = False) -> Image.Image:
    """Gera um ícone de 64x64 elegante e moderno com suporte a estado ativo."""
    size = (64, 64)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cores
    bg_color = (30, 41, 59, 255)       # Slate 800
    border_color = (59, 130, 246, 255) if not is_active else (34, 197, 94, 255) # Azul ou Verde
    accent = (96, 165, 250, 255)       # Cyan/Blue
    lens_color = (15, 23, 42, 255)

    # Base quadrada arredondada
    draw.rounded_rectangle([4, 4, 60, 60], radius=14, fill=bg_color, outline=border_color, width=3)

    # Corpo da câmera
    draw.rounded_rectangle([14, 22, 50, 48], radius=6, fill=accent)
    # Topo da câmera (flash/viewfinder)
    draw.rounded_rectangle([22, 16, 34, 22], radius=3, fill=accent)

    # Lente circular central
    draw.ellipse([24, 27, 40, 43], fill=lens_color, outline=(255, 255, 255, 220), width=2)
    # Brilho na lente
    draw.ellipse([27, 30, 31, 34], fill=(255, 255, 255, 240))

    # Se for o ícone de chamado ativo, desenha um indicador verde brilhante no canto superior direito
    if is_active:
        draw.ellipse([44, 6, 58, 20], fill=(34, 197, 94, 255), outline=(255, 255, 255, 255), width=2)

    return img

def main():
    assets_dir = Path(__file__).parent
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Ícone padrão (em repouso)
    icon_default = create_app_icon(is_active=False)
    icon_default.save(str(assets_dir / "icon.png"), "PNG")
    icon_default.save(str(assets_dir / "icon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    # Ícone com chamado ativo
    icon_active = create_app_icon(is_active=True)
    icon_active.save(str(assets_dir / "icon_active.png"), "PNG")
    icon_active.save(str(assets_dir / "icon_active.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    print("[Assets] Ícones gerados com sucesso em:", assets_dir)

if __name__ == "__main__":
    main()
