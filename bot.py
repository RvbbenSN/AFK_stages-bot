import ctypes
import os
import sys
import time

# Configurar DPI awareness en Windows antes de importar pyautogui/Pillow
if sys.platform == 'win32':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import pyautogui

import config

# Guardar la función print original y duplicar a bot.log con marcas de tiempo
_original_print = print

def print(*args, **kwargs):
    """Sobrescribe print para duplicar la salida en la consola y en bot.log con marcas de tiempo."""
    message = " ".join(str(arg) for arg in args)
    _original_print(*args, **kwargs)
    
    if message.strip() and not message.startswith("="):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        log_path = os.path.join(config.BASE_DIR, "bot.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            pass

# Importar componentes modulares del motor para re-exportación pública
from src.core.inputs import simulate_human_click
from src.core.vision import (
    TEMPLATES_CACHE,
    check_auto_skills_status,
    get_template_threshold,
    load_template,
    match_template_multi,
    match_template_single,
)
from src.core.window import get_game_window, standardize_window_size
from src.modules.afk_stages import (
    get_team_for_attempt,
    run_afk_stages,
    update_bot_stats,
)

# Alias de compatibilidad hacia atrás
run_bot = run_afk_stages

__all__ = [
    "TEMPLATES_CACHE",
    "check_auto_skills_status",
    "get_game_window",
    "get_team_for_attempt",
    "get_template_threshold",
    "load_template",
    "match_template_multi",
    "match_template_single",
    "run_afk_stages",
    "run_bot",
    "simulate_human_click",
    "standardize_window_size",
    "update_bot_stats",
]


if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n[INFO] Bot detenido manualmente por el usuario. ¡Hasta luego!")
    except pyautogui.FailSafeException:
        print("\n[INFO] Failsafe activado. Deteniendo el bot por seguridad.")
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error inesperado: {e}")
        input("Presiona ENTER para salir...")
