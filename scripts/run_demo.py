# Entrypoint simples; injeta o src/ no sys.path para usar código local.
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tycherion.app.main import run_app

if __name__ == "__main__":
    run_app(config_path=str(ROOT / "configs" / "demo.yaml"))
