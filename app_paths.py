"""Application resources and writable user data locations."""
from pathlib import Path
import os
import sys


def resource_dir() -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def lite_edition() -> bool:
    return (resource_dir() / 'lite-edition.flag').is_file()


def user_data_dir() -> Path:
    configured = os.getenv('ONEPAGER_DATA_DIR', '').strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if not getattr(sys, 'frozen', False):
        return resource_dir() / 'uploads'
    folder = 'TrainingOnePagerLite' if lite_edition() else 'TrainingOnePager'
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / folder
    if sys.platform == 'win32':
        return Path(os.getenv('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / folder
    return Path(os.getenv('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'training-onepager'


def bundled_tool(name: str) -> str | None:
    suffix = '.exe' if sys.platform == 'win32' and not name.lower().endswith('.exe') else ''
    candidate = resource_dir() / 'tools' / (name + suffix)
    return str(candidate) if candidate.is_file() else None
