import random
import time

import pyautogui

import config

# Seguridad de PyAutoGUI
pyautogui.FAILSAFE = True

def simulate_human_click(window, rel_x, rel_y):
    """
    Realiza un clic con desviación aleatoria, movimiento suave y retención del botón
    diseñado para juegos nativos y emuladores DirectX.
    """
    abs_x = window.left + rel_x
    abs_y = window.top + rel_y

    offset = getattr(config, "CLICK_OFFSET", 8)
    min_delay = getattr(config, "CLICK_MIN_DELAY", 0.05)
    max_delay = getattr(config, "CLICK_MAX_DELAY", 0.15)

    click_x = abs_x + random.randint(-offset, offset)
    click_y = abs_y + random.randint(-offset, offset)

    delay = random.uniform(min_delay, max_delay)
    if getattr(config, "DEBUG", False):
        print(f"[BOT] Esperando {delay:.2f}s antes de hacer clic en ({click_x}, {click_y})...")
    time.sleep(delay)

    try:
        window.activate()
    except Exception:
        pass

    # Mover el ratón suavemente al punto (evita saltos bruscos detectados por anti-cheats)
    pyautogui.moveTo(click_x, click_y, duration=random.uniform(0.08, 0.15))

    # Presionar y soltar con un retardo que emula un clic físico real
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.05, 0.10))
    pyautogui.mouseUp()
