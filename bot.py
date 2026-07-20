import sys
import ctypes

# Configurar DPI awareness en Windows antes de importar pyautogui/Pillow
# Esto soluciona problemas de coordenadas y tamaño cuando la pantalla tiene escala (ej. 125% o 150%)
if sys.platform == 'win32':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

import os
import time
import random
import cv2
import numpy as np
import pyautogui
import pygetwindow as gw
from PIL import ImageGrab

# Importar configuración
import config

# Guardar la función print original
_original_print = print

def print(*args, **kwargs):
    """Sobrescribe print para duplicar la salida en la consola y en bot.log con marcas de tiempo."""
    message = " ".join(str(arg) for arg in args)
    
    # Imprimir en consola usando el print original
    _original_print(*args, **kwargs)
    
    # Escribir en el archivo de log (evitando líneas vacías o divisores)
    if message.strip() and not message.startswith("="):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        log_path = os.path.join(config.BASE_DIR, "bot.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_line)
        except:
            pass

# Activar Failsafe de seguridad (llevar ratón a la esquina superior izquierda aborta el programa)
pyautogui.FAILSAFE = True

# Caché de imágenes cargadas
TEMPLATES_CACHE = {}

def get_game_window():
    """Busca la ventana del juego por sus posibles nombres, descartando consolas y scripts."""
    for title in config.GAME_WINDOW_TITLES:
        wins = gw.getWindowsWithTitle(title)
        for w in wins:
            # Descartar ventanas de consola, scripts de python, editores o el propio lanzador
            lower_title = w.title.lower()
            if any(x in lower_title for x in ["lanzador", "terminal", "cmd.exe", "powershell", "python", "code", "bot.py", "visual studio"]):
                continue
            if w.width > 150 and w.height > 150:
                return w
    return None

def load_template(base_name):
    """
    Busca una imagen en la carpeta images/ con extensión .jpg o .png.
    Retorna la imagen OpenCV BGR si existe, de lo contrario None.
    """
    if base_name in TEMPLATES_CACHE:
        return TEMPLATES_CACHE[base_name]
    
    # Intentar extensiones .jpg y .png
    for ext in [".jpg", ".png"]:
        # Quitar extensión existente si la tuviera
        name_clean = base_name
        for e in [".jpg", ".png"]:
            if name_clean.lower().endswith(e):
                name_clean = name_clean[:-len(e)]
                
        filename = name_clean + ext
        path = os.path.join(config.IMAGE_DIR, filename)
        if os.path.exists(path):
            template = cv2.imread(path)
            if template is not None:
                TEMPLATES_CACHE[base_name] = template
                if config.DEBUG:
                    print(f"[DEBUG] Plantilla '{base_name}' cargada con éxito como '{filename}'. Tamaño: {template.shape[1]}x{template.shape[0]}")
                return template
    return None

# Umbrales específicos por plantilla para evitar falsos positivos
TEMPLATE_THRESHOLDS = {
    "normal_challenge": 0.88,       # Botón pequeño "Battle" del selector
    "continuar_normal": 0.88,       # Botón pequeño "Battle" de victoria
    "battle": 0.80,                 # Botón grande "Battle" de preparación
    "victory": 0.80,
    "defeat": 0.80,
    "records": 0.80,
    "copy": 0.80,
    "retry": 0.80
}

def match_template_single(screenshot, template_name):
    """
    Busca un elemento en la captura de pantalla usando el nombre base de la plantilla.
    Retorna (confianza, (centro_x, centro_y)) o (0, None) si no hay coincidencia.
    """
    template = load_template(template_name)
    if template is None:
        return 0, None
        
    screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    threshold = TEMPLATE_THRESHOLDS.get(template_name, config.CONFIDENCE_THRESHOLD)
    
    if max_val >= threshold:
        h, w = template.shape[:2]
        cx = max_loc[0] + w // 2
        cy = max_loc[1] + h // 2
        return max_val, (cx, cy)
    return max_val, None

def simulate_human_click(window, rel_x, rel_y):
    """Realiza un clic con desviación aleatoria, movimiento suave y retención del botón para juegos DirectX."""
    abs_x = window.left + rel_x
    abs_y = window.top + rel_y
    
    click_x = abs_x + random.randint(-config.CLICK_OFFSET, config.CLICK_OFFSET)
    click_y = abs_y + random.randint(-config.CLICK_OFFSET, config.CLICK_OFFSET)
    
    delay = random.uniform(config.CLICK_MIN_DELAY, config.CLICK_MAX_DELAY)
    if config.DEBUG:
        print(f"[BOT] Esperando {delay:.2f}s antes de cliquear en ({click_x}, {click_y})...")
    time.sleep(delay)
    
    try:
        window.activate()
    except:
        pass
        
    # Mover el ratón suavemente al punto (evita saltos bruscos detectados por anti-cheats)
    pyautogui.moveTo(click_x, click_y, duration=random.uniform(0.15, 0.3))
    
    # Presionar y soltar con un retardo que emule un clic físico real
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.08, 0.15))
    pyautogui.mouseUp()

def run_bot():
    print("=" * 60)
    print("        BOT PERSONALIZADO DE AFK JOURNEY (FASES AFK)")
    print("=" * 60)
    print("Lógica activa:")
    print(" - Copiado de equipos 1 al 5 secuencialmente por intento.")
    print(" - Alterna modos (Battle <-> Phantimal) en caso de bloqueo.")
    print(" Failsafe: Mueve el ratón a la esquina superior izquierda para detener.")
    print(" Parar: Presiona Ctrl+C en esta ventana.")
    print("-" * 60)
    
    essential_templates = [
        "battle_modes", "AFK_stages", "normal_challenge", "phantimal_challenge",
        "records", "next_formation", "copy", "battle", "victory",
        "continuar_normal", "continuar_phantimal", "defeat", "retry", "atras"
    ]
    
    print("[INFO] Comprobando archivos de imágenes en images/:")
    missing_count = 0
    for name in essential_templates:
        t = load_template(name)
        if t is None:
            print(f"  [-] '{name}' -> NO ENCONTRADA")
            missing_count += 1
        else:
            print(f"  [+] '{name}' -> Lista")
            
    if missing_count > 0:
        print(f"\n[ADVERTENCIA] Faltan {missing_count} imágenes. El bot intentará correr, pero fallará si llega a esa pantalla.")
        print("Asegúrate de recortarlas con Snipping Tool o grab_template.py en la carpeta images/.")
    else:
        print("\n[OK] ¡Todas las imágenes requeridas están cargadas y listas!")
        
    # Inicialización del estado del bot
    default_mode_cfg = getattr(config, "DEFAULT_MODE", "random")
    if default_mode_cfg == "random":
        current_mode = random.choice(["battle", "phantimal"])
    else:
        current_mode = default_mode_cfg
        
    current_team_index = 0             # 0 = equipo 1, 1 = equipo 2, etc.
    consecutive_defeats = 0
    need_mode_switch = False
    connected_window_title = None
    no_match_count = 0
    team_already_copied = False
    battles_count = 0                  # Contador de combates para rotar cada 5 intentos
    
    print(f"\n[ESTADO INICIAL] Modo de inicio: {current_mode.upper()} | Equipo inicial: #{current_team_index + 1}")
    
    while True:
        matched = False
        window = get_game_window()
        if not window:
            print("[ADVERTENCIA] No se detecta la ventana del juego. Asegúrate de tenerlo abierto y no minimizado.")
            time.sleep(5)
            continue
            
        if window.title != connected_window_title:
            connected_window_title = window.title
            print(f"[OK] Conectado a la ventana del juego: '{window.title}' (Posición: {window.left},{window.top} | Tamaño: {window.width}x{window.height})")
            
            # Forzar tamaño de ventana si está configurado en config.py para estandarizar
            force_size = getattr(config, "FORCE_WINDOW_SIZE", None)
            if force_size:
                w, h = force_size
                if window.width != w or window.height != h:
                    print(f"[BOT] Ajustando tamaño de la ventana a {w}x{h} para estandarizar resoluciones...")
                    try:
                        window.resizeTo(w, h)
                        time.sleep(1.5) # Esperar a que se redimensione y redibuje
                        # Actualizar objeto de ventana
                        window = get_game_window()
                        if window:
                            print(f"[BOT] Tamaño ajustado con éxito. Nuevo tamaño: {window.width}x{window.height}")
                    except Exception as e:
                        print(f"[ADVERTENCIA] No se pudo redimensionar la ventana: {e}")

            
        # Capturar el monitor delimitando el área del juego (ROI perfecto para múltiples monitores)
        # Pillow utiliza coordenadas absolutas: (left, top, right, bottom)
        bbox = (window.left, window.top, window.left + window.width, window.top + window.height)
        try:
            screenshot = ImageGrab.grab(bbox=bbox, all_screens=True)
        except Exception as e:
            if config.DEBUG:
                print(f"[ERROR] Error al realizar captura de pantalla: {e}")
            time.sleep(2)
            continue
            
        # 1. VERIFICAR VICTORIA
        _, victory_pt = match_template_single(screenshot, "victory")
        if victory_pt:
            matched = True
            print(f"[VICTORIA] ¡Etapa superada con éxito!")
            # Resetear contadores de fallos
            current_team_index = 0
            consecutive_defeats = 0
            team_already_copied = False
            
            # Incrementar contador de batallas e intercalar si llegamos a 5
            battles_count += 1
            print(f"[BOT] Batalla completada en este modo ({battles_count}/5).")
            
            if battles_count >= 5:
                print("[MODO] Se han completado 5 batallas en este modo. Rotando al modo alternativo...")
                need_mode_switch = True
                battles_count = 0
                current_mode = "phantimal" if current_mode == "battle" else "battle"
                
                # Para cambiar de modo tras ganar, hacemos clic fuera del botón "continuar" (en el cartel de victoria).
                # Esto nos saca de forma nativa al selector general de etapas AFK.
                print("[BOT] Volviendo al mapa general para alternar modo...")
                simulate_human_click(window, victory_pt[0], victory_pt[1])
            else:
                need_mode_switch = False
                # Hacer clic en el botón de continuar según el modo activo
                btn_name = "continuar_normal" if current_mode == "battle" else "continuar_phantimal"
                _, cont_pt = match_template_single(screenshot, btn_name)
                
                if cont_pt:
                    print(f"[BOT] Avanzando a la siguiente etapa ({btn_name})...")
                    simulate_human_click(window, cont_pt[0], cont_pt[1])
                else:
                    # Fallback: hacer clic en el centro de la pantalla
                    print("[BOT] Pantalla de victoria detectada pero no veo el botón de continuar. Clic en el centro de victoria.")
                    simulate_human_click(window, victory_pt[0], victory_pt[1])
                
            time.sleep(config.LOOP_DELAY + 2.0)
            continue
            
        # 2. VERIFICAR DERROTA
        _, defeat_pt = match_template_single(screenshot, "defeat")
        if defeat_pt:
            matched = True
            consecutive_defeats += 1
            current_team_index += 1
            battles_count += 1
            team_already_copied = False
            print(f"[DERROTA] Falla en la etapa. Intentos en este modo: {battles_count}/5 | Derrotas consecutivas en esta etapa: {current_team_index}")
            
            # Comprobar si debemos alternar de modo por límite de batallas (5) o bloqueo en esta etapa
            if battles_count >= 5:
                print("[MODO] Se han completado 5 batallas en este modo. Rotando al modo alternativo...")
                need_mode_switch = True
                battles_count = 0
                current_team_index = 0
                current_mode = "phantimal" if current_mode == "battle" else "battle"
            elif current_team_index >= config.MAX_TEAMS_TO_TRY:
                print(f"[ATASCADO] Se probaron {config.MAX_TEAMS_TO_TRY} formaciones sin éxito. Rotando al modo alternativo...")
                need_mode_switch = True
                battles_count = 0
                current_team_index = 0
                current_mode = "phantimal" if current_mode == "battle" else "battle"
                
            # Buscar el botón de reintentar
            _, retry_pt = match_template_single(screenshot, "retry")
            if retry_pt:
                if need_mode_switch:
                    # En lugar de reintentar el combate, queremos salir para cambiar de pestaña.
                    # Buscamos el botón de retroceso (atrás) para volver al menú de selección
                    _, atras_pt = match_template_single(screenshot, "atras")
                    if atras_pt:
                        print("[BOT] Retrocediendo al menú principal de etapas para cambiar de pestaña...")
                        simulate_human_click(window, atras_pt[0], atras_pt[1])
                    else:
                        # Si no hay atrás en la pantalla de derrota, pulsamos retry y luego saldremos
                        print("[BOT] Volviendo a preparación para poder retroceder...")
                        simulate_human_click(window, retry_pt[0], retry_pt[1])
                else:
                    print("[BOT] Volviendo a preparación para reintentar con otra formación...")
                    simulate_human_click(window, retry_pt[0], retry_pt[1])
            else:
                # Si no encuentra el botón de reintentar pero ve derrota, clic en el texto para cerrar
                simulate_human_click(window, defeat_pt[0], defeat_pt[1])
                
            time.sleep(config.LOOP_DELAY + 2.0)
            continue
            
        # 3. CAMBIO DE MODO REQUERIDO (Atascado en un modo, volver al mapa principal de etapas)
        if need_mode_switch:
            # Comprobar si estamos en el menú de preparación (donde sale battle.jpg)
            _, battle_prep_pt = match_template_single(screenshot, "battle")
            if battle_prep_pt:
                matched = True
                # Si estamos preparando combate pero queremos cambiar de modo, debemos salir pulsando atrás
                _, atras_pt = match_template_single(screenshot, "atras")
                if atras_pt:
                    print("[BOT] Saliendo de la pantalla de preparación...")
                    simulate_human_click(window, atras_pt[0], atras_pt[1])
                    time.sleep(config.LOOP_DELAY + 1.5)
                    continue
                    
        # 4. PANTALLA DE PREPARACIÓN DEL COMBATE
        # Sabemos que estamos aquí si vemos el botón verde 'battle' o si el panel ya está abierto ('copy')
        _, battle_pt = match_template_single(screenshot, "battle")
        _, copy_pt = match_template_single(screenshot, "copy")
        if (battle_pt or copy_pt) and not need_mode_switch:
            matched = True
            
            # Si ya hemos copiado el equipo en esta fase, iniciamos combate directamente
            if team_already_copied:
                if battle_pt:
                    print("[BOT] Equipo ya configurado. Iniciando la batalla...")
                    simulate_human_click(window, battle_pt[0], battle_pt[1])
                    time.sleep(config.LOOP_DELAY + 2.5)
                else:
                    print("[ADVERTENCIA] Intentando iniciar batalla pero el botón 'battle' no es visible.")
                    # Si por alguna razón el panel se cerró mal, reintentamos el proceso de copiado en el siguiente ciclo
                    team_already_copied = False
                continue
            
            if not copy_pt:
                # El menú de récords está cerrado. Buscamos el botón para abrirlo
                _, record_pt = match_template_single(screenshot, "records")
                if record_pt:
                    print("[BOT] Abriendo el panel de formaciones de la comunidad...")
                    simulate_human_click(window, record_pt[0], record_pt[1])
                    time.sleep(config.LOOP_DELAY + 1.0)
                else:
                    # Si no encuentra el botón de registros, empezamos combate con lo que haya
                    print("[ADVERTENCIA] Botón de registros no encontrado. Iniciando combate por defecto...")
                    if battle_pt:
                        simulate_human_click(window, battle_pt[0], battle_pt[1])
                        time.sleep(config.LOOP_DELAY + 2.0)
                continue
            else:
                # El panel de registros está abierto.
                # Para seleccionar el equipo 'current_team_index' (0 a 4), pulsamos 'next_formation' N veces
                if current_team_index > 0:
                    print(f"[RECORDS] Avanzando {current_team_index} veces para llegar a la formación #{current_team_index + 1}...")
                    _, next_pt = match_template_single(screenshot, "next_formation")
                    
                    if next_pt:
                        for i in range(current_team_index):
                            print(f"  -> Clic en Siguiente Formación ({i+1}/{current_team_index})")
                            simulate_human_click(window, next_pt[0], next_pt[1])
                            time.sleep(0.8) # Espera pequeña para que cargue la visual
                    else:
                        print("[ADVERTENCIA] No se encontró el botón de 'next_formation'. Usando la formación por defecto.")
                        
                # Volver a buscar el botón 'copy' actualizado en pantalla y pulsarlo
                # Capturamos de nuevo para seguridad de coordenadas
                try:
                    new_screen = ImageGrab.grab(bbox=bbox, all_screens=True)
                    _, fresh_copy_pt = match_template_single(new_screen, "copy")
                except:
                    fresh_copy_pt = copy_pt
                    
                if fresh_copy_pt:
                    print(f"[BOT] Copiando formación seleccionada (Índice: {current_team_index})...")
                    simulate_human_click(window, fresh_copy_pt[0], fresh_copy_pt[1])
                    team_already_copied = True
                    time.sleep(1.8) # Espera para aplicar héroes y que se cierre el panel
                    
                continue
                
        # 5. MENÚ DE SELECCIÓN DE ETAPAS AFK (Phantimal vs Normal Battle)
        # Identificar si estamos en este menú buscando los botones challenge correspondientes
        _, normal_chall_pt = match_template_single(screenshot, "normal_challenge")
        _, phant_chall_pt = match_template_single(screenshot, "phantimal_challenge")
        
        if normal_chall_pt or phant_chall_pt:
            matched = True
            # Si estamos aquí, podemos apagar la bandera de cambio de modo ya que estamos en el selector
            need_mode_switch = False
            
            if current_mode == "battle" and normal_chall_pt:
                print("[BOT] Seleccionando modo BATTLE NORMAL...")
                simulate_human_click(window, normal_chall_pt[0], normal_chall_pt[1])
            elif current_mode == "phantimal" and phant_chall_pt:
                print("[BOT] Seleccionando modo PHANTIMAL CHALLENGE...")
                simulate_human_click(window, phant_chall_pt[0], phant_chall_pt[1])
            else:
                # Si no está visible el botón correcto pero sí el otro, puede que haya que hacer clic en él
                fallback_pt = normal_chall_pt if normal_chall_pt else phant_chall_pt
                print(f"[BOT] Entrando a la etapa disponible...")
                simulate_human_click(window, fallback_pt[0], fallback_pt[1])
                
            time.sleep(config.LOOP_DELAY + 2.0)
            continue
                
        # 6. ENTRADA GENERAL DESDE EL MENÚ DE INICIO / NAVEGACIÓN
        # Si vemos 'AFK_stages' en el menú de modos, hacemos clic
        _, stages_pt = match_template_single(screenshot, "AFK_stages")
        if stages_pt:
            matched = True
            print("[BOT] Entrando a AFK Stages...")
            simulate_human_click(window, stages_pt[0], stages_pt[1])
            time.sleep(config.LOOP_DELAY + 1.0)
            continue
            
        # Si estamos en el lobby principal y vemos 'battle_modes', hacemos clic
        _, modes_pt = match_template_single(screenshot, "battle_modes")
        if modes_pt:
            matched = True
            print("[BOT] Entrando al menú de Modos de Batalla...")
            simulate_human_click(window, modes_pt[0], modes_pt[1])
            time.sleep(config.LOOP_DELAY + 1.0)
            continue
            
        # 7. SOPORTE DE POPUPS GENERALES / CERRAR RECOMPENSAS
        _, cerrar_pt = match_template_single(screenshot, "cerrar")
        if cerrar_pt and not battle_pt:
            matched = True
            print("[BOT] Cerrando popup detectado en pantalla...")
            simulate_human_click(window, cerrar_pt[0], cerrar_pt[1])
            time.sleep(config.LOOP_DELAY)
            continue
            
        # Espera pasiva del bucle si no hay coincidencias
        if not matched:
            no_match_count += 1
            if no_match_count % 5 == 0:
                print(f"[INFO] Buscando coincidencias... (Ciclo {no_match_count} sin clics)")
                if config.DEBUG:
                    scores = []
                    # Mostrar el puntaje de coincidencia de las plantillas más representativas
                    for name in ["battle_modes", "AFK_stages", "battle", "victory", "defeat", "copy", "records", "next_formation"]:
                        conf, _ = match_template_single(screenshot, name)
                        scores.append(f"{name}: {conf:.2f}")
                    print(f"       -> Confianzas: {', '.join(scores)} (Umbral: {config.CONFIDENCE_THRESHOLD})")
        else:
            no_match_count = 0
            
        time.sleep(config.LOOP_DELAY)


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
