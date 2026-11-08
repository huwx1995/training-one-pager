"""Application resources and writable user data locations."""
from pathlib import Path
import os
import sys


def resource_dir() -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def user_data_dir() -> Path:
    configured = os.getenv('ONEPAGER_DATA_DIR', '').strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if not getattr(sys, 'frozen', False):
        return resource_dir() / 'uploads'
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'TrainingOnePager'
    if sys.platform == 'win32':
        return Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'TrainingOnePager'
    return Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'training-onepager'


def bundled_tool(name: str) -> str | None:
    candidate = resource_dir() / 'tools' / name
    return str(candidate) if candidate.is_file() else None
