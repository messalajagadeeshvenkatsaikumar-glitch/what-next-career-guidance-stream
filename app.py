from pathlib import Path
import sys


APP_DIR = Path(__file__).resolve().parent / "what-next career guidance stream"
APP_FILE = APP_DIR / "app.py"
sys.path.insert(0, str(APP_DIR))
__file__ = str(APP_FILE)

with APP_FILE.open(encoding="utf-8") as source:
    exec(compile(source.read(), str(APP_FILE), "exec"), globals())
