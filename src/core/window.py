import time

import pygetwindow as gw

import config


def get_game_window():
    """
    Busca la ventana del juego por sus posibles nombres configurados en GAME_WINDOW_TITLES,
    descartando consolas, scripts, editores o paneles del propio bot.
    """
    titles = getattr(config, "GAME_WINDOW_TITLES", ["AFK Journey", "AFK_Journey"])
    discard_keywords = [
        "lanzador", "terminal", "cmd.exe", "powershell", "python",
        "code", "bot.py", "visual studio", "panel de control", "dashboard"
    ]

    for title in titles:
        wins = gw.getWindowsWithTitle(title)
        for w in wins:
            lower_title = w.title.lower()
            if any(x in lower_title for x in discard_keywords):
                continue
            if w.width > 150 and w.height > 150:
                return w
    return None

def standardize_window_size(window, force_size=None):
    """
    Fuerza el tamaño de la ventana al valor especificado para estandarizar resoluciones.
    Retorna la ventana actualizada.
    """
    target_size = force_size or getattr(config, "FORCE_WINDOW_SIZE", (1616, 939))
    if not target_size or not window:
        return window

    w, h = target_size
    if window.width != w or window.height != h:
        print(f"[BOT] Ajustando tamaño de la ventana a {w}x{h} para estandarizar resoluciones...")
        try:
            window.resizeTo(w, h)
            time.sleep(1.5)  # Espera para redibujado
            fresh_w = get_game_window()
            if fresh_w:
                print(f"[BOT] Tamaño ajustado con éxito. Nuevo tamaño: {fresh_w.width}x{fresh_w.height}")
                return fresh_w
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudo redimensionar la ventana: {e}")

    return window
