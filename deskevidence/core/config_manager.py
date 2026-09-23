import os
import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_HOTKEYS = {
    "capture": "ctrl+shift+e",         # Captura janela ativa (ou tela inteira)
    "ticket_action": "ctrl+shift+p",   # Novo chamado ou gerenciar/finalizar chamado ativo
    "switch_ticket": "ctrl+shift+t",   # Trocar chamado ativo rapidamente
    "open_settings": "ctrl+shift+c",   # Abrir tela de configurações
}

def get_default_storage_path() -> str:
    """Retorna uma pasta padrão para armazenamento das evidências dentro dos Documentos do usuário."""
    home = Path.home()
    default_dir = home / "Documents" / "DeskEvidence_Evidencias"
    try:
        default_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback local se não puder criar em Documentos
        default_dir = Path("./Evidencias").resolve()
        default_dir.mkdir(parents=True, exist_ok=True)
    return str(default_dir)

DEFAULT_CONFIG: Dict[str, Any] = {
    "storage_folder": "",  # Preenchido dinamicamente na inicialização
    "capture_mode": "active_window",  # 'active_window' ou 'fullscreen'
    "prompt_quick_note": True,        # Exibir popup leve para descrição da evidência
    "generate_html_on_finish": True,  # Gerar relatório HTML automático ao finalizar
    "hotkeys": DEFAULT_HOTKEYS,
    "last_active_ticket_id": None,
    "theme": "dark",                  # 'dark' ou 'light'
}

class ConfigManager:
    """Gerenciador de configurações persistentes do DeskEvidence."""

    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            appdata = os.getenv("APPDATA")
            if appdata:
                self.config_dir = Path(appdata) / "DeskEvidence"
            else:
                self.config_dir = Path("./config").resolve()
        else:
            self.config_dir = Path(config_dir)

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "settings.json"
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo ou cria os padrões se não existir."""
        if not self.config_file.exists():
            self._data = dict(DEFAULT_CONFIG)
            if not self._data.get("storage_folder"):
                self._data["storage_folder"] = get_default_storage_path()
            self.save()
            return self._data

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            
            # Mescla com defaults para garantir campos novos
            merged = dict(DEFAULT_CONFIG)
            merged.update(loaded)
            
            # Garantir subchaves de hotkeys
            hotkeys = dict(DEFAULT_HOTKEYS)
            hotkeys.update(loaded.get("hotkeys", {}))
            merged["hotkeys"] = hotkeys

            if not merged.get("storage_folder"):
                merged["storage_folder"] = get_default_storage_path()

            self._data = merged
        except Exception as e:
            print(f"[ConfigManager] Erro ao carregar config ({e}). Usando defaults.")
            self._data = dict(DEFAULT_CONFIG)
            self._data["storage_folder"] = get_default_storage_path()
            self.save()

        return self._data

    def save(self) -> bool:
        """Salva as configurações atuais no arquivo JSON."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ConfigManager] Erro ao salvar config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def get_hotkey(self, action: str) -> str:
        hotkeys = self._data.get("hotkeys", DEFAULT_HOTKEYS)
        return hotkeys.get(action, DEFAULT_HOTKEYS.get(action, ""))

    def set_hotkey(self, action: str, combination: str) -> None:
        if "hotkeys" not in self._data:
            self._data["hotkeys"] = dict(DEFAULT_HOTKEYS)
        self._data["hotkeys"][action] = combination.strip().lower()
        self.save()

    @property
    def storage_folder(self) -> Path:
        path_str = self._data.get("storage_folder")
        if not path_str:
            path_str = get_default_storage_path()
            self.set("storage_folder", path_str)
        p = Path(path_str)
        p.mkdir(parents=True, exist_ok=True)
        return p
