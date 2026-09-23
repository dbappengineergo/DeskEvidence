import threading
import time
from typing import Callable, Dict, Optional, Tuple
import win32con
import win32gui
import win32api

# Mapa de nomes de teclas amigáveis para Virtual-Key Codes do Windows
VK_MAP: Dict[str, int] = {
    # Letras
    **{chr(c).lower(): c for c in range(ord('A'), ord('Z') + 1)},
    # Dígitos
    **{str(c): ord(str(c)) for c in range(10)},
    # Teclas de Função
    **{f"f{i}": getattr(win32con, f"VK_F{i}") for i in range(1, 25)},
    # Especiais
    "printscreen": win32con.VK_SNAPSHOT,
    "prtscn": win32con.VK_SNAPSHOT,
    "space": win32con.VK_SPACE,
    "tab": win32con.VK_TAB,
    "enter": win32con.VK_RETURN,
    "return": win32con.VK_RETURN,
    "esc": win32con.VK_ESCAPE,
    "escape": win32con.VK_ESCAPE,
    "backspace": win32con.VK_BACK,
    "insert": win32con.VK_INSERT,
    "delete": win32con.VK_DELETE,
    "home": win32con.VK_HOME,
    "end": win32con.VK_END,
    "pageup": win32con.VK_PRIOR,
    "pagedown": win32con.VK_NEXT,
    "up": win32con.VK_UP,
    "down": win32con.VK_DOWN,
    "left": win32con.VK_LEFT,
    "right": win32con.VK_RIGHT,
}

MODIFIERS_MAP: Dict[str, int] = {
    "alt": win32con.MOD_ALT,
    "ctrl": win32con.MOD_CONTROL,
    "control": win32con.MOD_CONTROL,
    "shift": win32con.MOD_SHIFT,
    "win": win32con.MOD_WIN,
    "super": win32con.MOD_WIN,
}

MOD_NOREPEAT = 0x4000  # Evita disparos múltiplos se segurar a tecla

def parse_hotkey_string(hotkey_str: str) -> Optional[Tuple[int, int]]:
    """
    Converte strings como 'ctrl+shift+e' ou 'ctrl+f10' para (modifiers, vk_code).
    """
    parts = [p.strip().lower() for p in hotkey_str.split("+") if p.strip()]
    if not parts:
        return None

    mods = MOD_NOREPEAT
    key = None

    for part in parts:
        if part in MODIFIERS_MAP:
            mods |= MODIFIERS_MAP[part]
        elif part in VK_MAP:
            key = VK_MAP[part]
        else:
            # Fallback para tecla de caractere simples
            if len(part) == 1:
                key = ord(part.upper())

    if key is None:
        return None

    return (mods, key)


class HotkeyManager:
    """
    Gerencia atalhos de teclado globais usando a API nativa RegisterHotKey do Windows.
    Roda em uma thread dedicada para escuta de mensagens sem bloquear o loop principal da UI.
    """

    def __init__(self):
        self._callbacks: Dict[int, Callable[[], None]] = {}
        self._hotkey_strings: Dict[int, str] = {}
        self._next_id = 1
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._registered_ids = set()

    def register_hotkey(self, hotkey_str: str, callback: Callable[[], None]) -> Optional[int]:
        """Registra uma função de callback para a combinação informada."""
        parsed = parse_hotkey_string(hotkey_str)
        if not parsed:
            print(f"[HotkeyManager] Combinação inválida ou não suportada: '{hotkey_str}'")
            return None

        with self._lock:
            hk_id = self._next_id
            self._next_id += 1
            self._callbacks[hk_id] = callback
            self._hotkey_strings[hk_id] = hotkey_str

        # Se a thread de mensagens já estiver rodando, reiniciamos os registros
        if self._thread and self._thread.is_alive():
            self._reload_hotkeys()

        return hk_id

    def unregister_all(self):
        with self._lock:
            self._callbacks.clear()
            self._hotkey_strings.clear()
        if self._thread and self._thread.is_alive():
            self._reload_hotkeys()

    def start(self):
        """Inicia a thread de escuta dos atalhos."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._message_loop, daemon=True, name="HotkeyMessageLoop")
        self._thread.start()

    def stop(self):
        """Para a thread de escuta."""
        self._stop_event.set()
        if self._thread_id:
            try:
                # Envia mensagem WM_QUIT para acordar e finalizar o GetMessage
                win32api.PostThreadMessage(self._thread_id, win32con.WM_QUIT, 0, 0)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        self._thread_id = None

    def _reload_hotkeys(self):
        """Notifica a thread do message loop para recarregar as hotkeys."""
        if self._thread_id:
            try:
                # Posta uma mensagem customizada (WM_USER + 1) para a thread recadastrar
                win32api.PostThreadMessage(self._thread_id, win32con.WM_USER + 1, 0, 0)
            except Exception:
                pass

    def _do_register_all(self):
        """Executado exclusivamente dentro da thread do message loop."""
        # Primeiro desregistra os antigos
        for hk_id in list(self._registered_ids):
            try:
                win32gui.UnregisterHotKey(None, hk_id)
            except Exception:
                pass
        self._registered_ids.clear()

        # Registra os atuais
        with self._lock:
            items = list(self._hotkey_strings.items())

        for hk_id, hk_str in items:
            parsed = parse_hotkey_string(hk_str)
            if not parsed:
                continue
            mods, vk = parsed
            try:
                success = win32gui.RegisterHotKey(None, hk_id, mods, vk)
                if success:
                    self._registered_ids.add(hk_id)
                else:
                    print(f"[HotkeyManager] Falha ao registrar '{hk_str}' (id={hk_id}). Código de erro: {win32api.GetLastError()}")
            except Exception as e:
                print(f"[HotkeyManager] Exceção ao registrar hotkey '{hk_str}': {e}")

    def _message_loop(self):
        """Loop de mensagens Win32 em thread dedicada."""
        self._thread_id = win32api.GetCurrentThreadId()
        self._do_register_all()

        while not self._stop_event.is_set():
            try:
                # PeekMessage com delay ou GetMessage
                # win32gui.GetMessage(hwnd, minMsg, maxMsg)
                ret, msg = win32gui.GetMessage(None, 0, 0)
                if ret == 0 or ret == -1:
                    # WM_QUIT recebido ou erro
                    break

                msg_id = msg[1]
                wParam = msg[2] # id do hotkey

                if msg_id == win32con.WM_HOTKEY:
                    callback = None
                    with self._lock:
                        callback = self._callbacks.get(wParam)
                    if callback:
                        try:
                            # Dispara o callback em uma micro-thread para não atrasar o loop
                            threading.Thread(target=callback, daemon=True).start()
                        except Exception as e:
                            print(f"[HotkeyManager] Erro no callback do hotkey {wParam}: {e}")

                elif msg_id == win32con.WM_USER + 1:
                    # Solicitação para recarregar hotkeys
                    self._do_register_all()

                win32gui.TranslateMessage(msg)
                win32gui.DispatchMessage(msg)

            except Exception as e:
                if self._stop_event.is_set():
                    break
                time.sleep(0.05)

        # Cleanup final ao sair
        for hk_id in list(self._registered_ids):
            try:
                win32gui.UnregisterHotKey(None, hk_id)
            except Exception:
                pass
        self._registered_ids.clear()
