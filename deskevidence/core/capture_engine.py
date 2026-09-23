import ctypes
from ctypes import wintypes
import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PIL import Image, ImageGrab
import win32gui
import win32process

# Configura DPI awareness para coordenadas precisas em telas 4K / High-DPI
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per monitor v2
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Constante da DWM API para obter o retângulo visível exato da janela (sem a sombra invisível)
DWMWA_EXTENDED_FRAME_BOUNDS = 9

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]

def get_accurate_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """Obtém as coordenadas exatas da janela visível via DWM (DwmGetWindowAttribute)."""
    rect = RECT()
    try:
        hr = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            wintypes.HWND(hwnd),
            wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
            ctypes.byref(rect),
            ctypes.sizeof(rect)
        )
        if hr == 0:
            return (rect.left, rect.top, rect.right, rect.bottom)
    except Exception:
        pass
    
    # Fallback para win32gui
    return win32gui.GetWindowRect(hwnd)

def get_process_name_from_hwnd(hwnd: int) -> str:
    """Tenta obter o nome do executável da janela ativa."""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        import psutil
        return psutil.Process(pid).name()
    except Exception:
        return "Mudar aqui"

class CaptureResult:
    def __init__(self, image: Image.Image, metadata: Dict[str, Any]):
        self.image = image
        self.metadata = metadata

class CaptureEngine:
    """Motor de captura de screenshots com suporte a Janela Ativa e Tela Cheia."""

    def __init__(self, mode: str = "active_window"):
        self.mode = mode  # 'active_window' ou 'fullscreen'

    def capture(self, override_mode: Optional[str] = None) -> Optional[CaptureResult]:
        """Tira o screenshot de acordo com o modo configurado."""
        active_mode = override_mode or self.mode
        now = datetime.datetime.now()
        timestamp_iso = now.isoformat()
        timestamp_display = now.strftime("%d/%m/%Y %H:%M:%S")

        if active_mode == "fullscreen":
            return self._capture_fullscreen(timestamp_iso, timestamp_display)
        else:
            return self._capture_active_window(timestamp_iso, timestamp_display)

    def _capture_fullscreen(self, timestamp_iso: str, timestamp_display: str) -> Optional[CaptureResult]:
        """Captura toda a área do monitor."""
        try:
            # all_screens=True captura múltiplos monitores se existirem
            screenshot = ImageGrab.grab(all_screens=True)
            metadata = {
                "timestamp": timestamp_iso,
                "timestamp_display": timestamp_display,
                "mode": "fullscreen",
                "window_title": "Área de Trabalho (Tela Inteira)",
                "process_name": "explorer.exe",
                "width": screenshot.width,
                "height": screenshot.height,
            }
            return CaptureResult(screenshot, metadata)
        except Exception as e:
            print(f"[CaptureEngine] Erro ao capturar tela inteira: {e}")
            return None

    def _capture_active_window(self, timestamp_iso: str, timestamp_display: str) -> Optional[CaptureResult]:
        """Captura especificamente a janela que está em foco (ativa)."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                # Se não houver janela ativa definida, faz fallback para tela inteira
                return self._capture_fullscreen(timestamp_iso, timestamp_display)

            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                title = "Janela sem título"

            process_name = get_process_name_from_hwnd(hwnd)
            left, top, right, bottom = get_accurate_window_rect(hwnd)
            width = right - left
            height = bottom - top

            # Validação se as dimensões são válidas
            if width <= 10 or height <= 10:
                return self._capture_fullscreen(timestamp_iso, timestamp_display)

            # Efetua o recorte exato da janela
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
            
            metadata = {
                "timestamp": timestamp_iso,
                "timestamp_display": timestamp_display,
                "mode": "active_window",
                "window_title": title,
                "process_name": process_name,
                "bounds": [left, top, right, bottom],
                "width": screenshot.width,
                "height": screenshot.height,
            }
            return CaptureResult(screenshot, metadata)
        except Exception as e:
            print(f"[CaptureEngine] Erro ao capturar janela ativa: {e}. Tentando fullscreen.")
            return self._capture_fullscreen(timestamp_iso, timestamp_display)
