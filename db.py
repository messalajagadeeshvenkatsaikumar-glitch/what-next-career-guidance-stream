from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

APP_DIR = Path(__file__).resolve().parent / "what-next career guidance stream"
_SPEC = spec_from_file_location("legacy_project_db", APP_DIR / "db.py")
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Could not load app database module from {APP_DIR / 'db.py'}")

_module = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _module
_SPEC.loader.exec_module(_module)

for _name in dir(_module):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_module, _name)

BASE_DIR = APP_DIR
