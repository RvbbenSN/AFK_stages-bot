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
            if any(x in lower_title for x in ["lanzador", "terminal", "cmd.exe", "powershell", "python", "code", "bot.py", "visual studio", "panel de control", "dashboard"]):
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
    "retry": 0.80,
    "cancel_no-heroe": 0.80,
    "formations_btn": 0.80,
    "AFKST1": 0.80,
    "AFKST2": 0.80,
    "use_btn": 0.80,
    "battle_modes": 0.70,
    "AFK_stages": 0.70,
    "green_tick": 0.80,
    "tap_to_exit": 0.80,
    "auto_off": 0.86,
    "auto_on": 0.86
}

def match_template_single(screen_cv, template_name):
    """
    Busca un elemento en la captura de pantalla OpenCV (screen_cv).
    Retorna (confianza, (centro_x, centro_y)) o (0, None) si no hay coincidencia.
    """
    template = load_template(template_name)
    if template is None:
        return 0, None
        
    result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    threshold = TEMPLATE_THRESHOLDS.get(template_name, config.CONFIDENCE_THRESHOLD)
    
    if max_val >= threshold:
        h, w = template.shape[:2]
        cx = max_loc[0] + w // 2
        cy = max_loc[1] + h // 2
        return max_val, (cx, cy)
    return max_val, None

def match_template_multi(screen_cv, template_name):
    """
    Busca todas las ocurrencias de un elemento en la captura de pantalla OpenCV (screen_cv).
    Retorna una lista de coordenadas (centro_x, centro_y).
    """
    template = load_template(template_name)
    if template is None:
        return []
        
    result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
    threshold = TEMPLATE_THRESHOLDS.get(template_name, config.CONFIDENCE_THRESHOLD)
    
    loc = np.where(result >= threshold)
    h, w = template.shape[:2]
    
    points = []
    # Supresión de no-máximos simple para agrupar píxeles vecinos
    for pt in zip(*loc[::-1]):
        cx = pt[0] + w // 2
        cy = pt[1] + h // 2
        
        too_close = False
        for px, py in points:
            if abs(py - cy) < h // 2 and abs(px - cx) < w // 2:
                too_close = True
                break
        if not too_close:
            points.append((cx, cy))
            
    return points

def check_auto_skills_status(screen_cv):
    """
    Comprueba el estado del botón de lanzamiento automático de habilidades durante el combate.
    Retorna (status, point) donde:
      - status: 'OFF' (icono gris apagado), 'ON' (icono dorado encendido), o 'UNKNOWN'
      - point: (rel_x, rel_y) para hacer clic en el botón si está apagado
    """
    score_off, pt_off = match_template_single(screen_cv, "auto_off")
    score_on, pt_on = match_template_single(screen_cv, "auto_on")

    # Si detectamos el icono apagado con buena confianza y supera al encendido
    if score_off >= 0.86 and score_off > (score_on + 0.04):
        return "OFF", pt_off
    elif score_on >= 0.86:
        return "ON", pt_on
    return "UNKNOWN", None

def get_team_for_attempt(stage_attempt, max_known_community=None):
    """
    Calcula el tipo de equipo, su valor/índice y si pertenece a la Fase 1 (barrido rápido)
    o a la Fase 2 (insistencia con subintentos).
    Retorna (team_type, team_value, is_fast_sweep)
    Donde:
      - team_type: "community" o "custom"
      - team_value: índice entero (0 a 9) para community, o nombre de plantilla (str) para custom
      - is_fast_sweep: True (1 intento rápido) o False (subintentos completos de insistencia)
    """
    use_custom = getattr(config, "USE_CUSTOM_FORMATIONS", True)
    max_teams = max_known_community if (max_known_community is not None and max_known_community > 0) else 10

    # 1. FASE 1: BARRIDO RÁPIDO (1 intento por formación para victoria rápida)
    fast_sweep_steps = []
    
    # Primero formaciones impares de la comunidad: #1 (idx 0), #3 (idx 2), #5 (idx 4), #7 (idx 6), #9 (idx 8)
    for idx in [0, 2, 4, 6, 8]:
        if idx < max_teams:
            fast_sweep_steps.append(("community", idx, True))
            
    # Luego formaciones pares de la comunidad: #2 (idx 1), #4 (idx 3), #6 (idx 5), #8 (idx 7)
    for idx in [1, 3, 5, 7]:
        if idx < max_teams:
            fast_sweep_steps.append(("community", idx, True))
            
    # Al final del barrido, las formaciones guardadas (si están activadas)
    if use_custom:
        fast_sweep_steps.append(("custom", "AFKST1", True))
        fast_sweep_steps.append(("custom", "AFKST2", True))

    # 2. FASE 2: INSISTENCIA POR RNG (aplica los subintentos configurados en el slider)
    insist_steps = []
    
    # Siempre insistir primero en Comunidad #1
    if 0 < max_teams:
        insist_steps.append(("community", 0, False))
        
    # Insistir en personalizadas si están activas
    if use_custom:
        insist_steps.append(("custom", "AFKST1", False))
        insist_steps.append(("custom", "AFKST2", False))
        
    # Insistir en Comunidad #2 y #3 (si existen)
    for idx in [1, 2]:
        if idx < max_teams:
            insist_steps.append(("community", idx, False))
            
    # Insistir en Comunidad #4 y #5 (si existen)
    for idx in [3, 4]:
        if idx < max_teams:
            insist_steps.append(("community", idx, False))

    # Combinar el plan completo de la etapa
    all_steps = fast_sweep_steps + insist_steps
    if not all_steps:
        return "community", 0, False

    if stage_attempt < len(all_steps):
        return all_steps[stage_attempt]
    else:
        # Si se superan los pasos definidos, ciclar sobre las opciones de insistencia
        pool = insist_steps if insist_steps else all_steps
        fallback_idx = (stage_attempt - len(all_steps)) % len(pool)
        return pool[fallback_idx]

def update_bot_stats(mode=None, stage_attempt=None, sub_attempt=None, max_sub_attempts=None,
                     team_info=None, battle_state=None, last_battle_duration=None,
                     victories_session=None, defeats_session=None, defeats_consecutive=None,
                     stages_normal=None, stages_phantimal=None, stages_total=None):
    """Actualiza de forma segura el diccionario global BOT_STATS para la GUI en tiempo real."""
    stats = getattr(config, "BOT_STATS", None)
    if not isinstance(stats, dict):
        return
    if mode is not None: stats["mode"] = mode
    if stage_attempt is not None: stats["stage_attempt"] = stage_attempt
    if sub_attempt is not None: stats["sub_attempt"] = sub_attempt
    if max_sub_attempts is not None: stats["max_sub_attempts"] = max_sub_attempts
    if team_info is not None: stats["team_info"] = team_info
    if battle_state is not None: stats["battle_state"] = battle_state
    if last_battle_duration is not None: stats["last_battle_duration"] = str(last_battle_duration)
    if victories_session is not None: stats["victories_session"] = victories_session
    if defeats_session is not None: stats["defeats_session"] = defeats_session
    if defeats_consecutive is not None: stats["defeats_consecutive"] = defeats_consecutive
    if stages_normal is not None: stats["stages_normal"] = stages_normal
    if stages_phantimal is not None: stats["stages_phantimal"] = stages_phantimal
    if stages_total is not None: stats["stages_total"] = stages_total

def simulate_human_click(window, rel_x, rel_y):
    """Realiza un clic con desviación aleatoria, movimiento suave y retención del botón para juegos DirectX."""
    abs_x = window.left + rel_x
    abs_y = window.top + rel_y
    
    click_x = abs_x + random.randint(-config.CLICK_OFFSET, config.CLICK_OFFSET)
    click_y = abs_y + random.randint(-config.CLICK_OFFSET, config.CLICK_OFFSET)
    
    delay = random.uniform(config.CLICK_MIN_DELAY, config.CLICK_MAX_DELAY)
    if config.DEBUG:
        print(f"[BOT] Esperando {delay:.2f}s antes de hacer clic en ({click_x}, {click_y})...")
    time.sleep(delay)
    
    try:
        window.activate()
    except:
        pass
        
    # Mover el ratón suavemente al punto (evita saltos bruscos detectados por anti-cheats)
    pyautogui.moveTo(click_x, click_y, duration=random.uniform(0.08, 0.15))
    
    # Presionar y soltar con un retardo que emule un clic físico real
    pyautogui.mouseDown()
    time.sleep(random.uniform(0.05, 0.10))
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
        "continuar_normal", "continuar_phantimal", "defeat", "retry", "atras",
        "cancel_no-heroe", "formations_btn", "AFKST1", "AFKST2", "use_btn", "green_tick",
        "tap_to_exit", "auto_off", "auto_on"
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
    consecutive_defeats = 0            # Derrotas consecutivas globales (límite 30)
    need_mode_switch = False
    connected_window_title = None
    no_match_count = 0
    team_already_copied = False
    battles_count = 0                  # Contador de combates para rotar cada 5 intentos
    stages_cleared_normal = 0          # Contador de victorias normales en la sesión
    stages_cleared_phantimal = 0       # Contador de victorias phantimal en la sesión
    stage_attempt = 0                  # Intentos en la etapa actual en este modo (límite 20)
    sub_attempt = 0                    # Subintentos con la formación actual (0 a 4)
    max_known_community_teams = None   # Máximo de formaciones comunitarias descubiertas en el nivel actual
    mode_locked = False                # Si está bloqueado en un modo por haber fallado 20 veces en el otro
    current_displayed_team_index = 0   # Índice de formación que está actualmente visible en pantalla
    team_type = "community"            # "community" o "custom"
    custom_name = None                 # Nombre de la formación personalizada ("AFKST1" o "AFKST2")
    in_battle = False                  # Bandera de combate activo
    auto_verified_on = False           # Bandera para evitar chequeos redundantes de auto-habilidades
    auto_was_disabled = False          # Si se detectó apagado en el combate actual (no contará intento si pierde)
    battle_start_time = None           # Marca de tiempo de inicio del combate actual
    last_battle_duration = "0.0s"      # Duración de la última batalla
    victories_session = 0              # Victorias totales en sesión
    defeats_session = 0                # Derrotas totales en sesión
    
    print(f"\n[ESTADO INICIAL] Modo de inicio: {current_mode.upper()} | Equipo inicial: #{current_team_index + 1}")
    
    while True:
        # Detener la ejecución si se solicita desde la interfaz gráfica
        if not getattr(config, "BOT_RUNNING", True):
            print("[BOT] Detención solicitada. Saliendo de la ejecución...")
            break

        matched = False
        window = get_game_window()
        if not window:
            print("[ADVERTENCIA] No se detecta la ventana del juego. Asegúrate de tenerlo abierto y no minimizado.")
            # Espera corta dividida para mantener la interfaz responsive al detener
            for _ in range(6):
                if not getattr(config, "BOT_RUNNING", True):
                    break
                time.sleep(0.5)
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
            screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            if config.DEBUG:
                print(f"[ERROR] Error al realizar captura de pantalla: {e}")
            time.sleep(2)
            continue
            
        # Resolver dinámicamente el equipo a utilizar basado en stage_attempt y tope de comunidad conocido
        team_type, team_value, is_fast_sweep = get_team_for_attempt(stage_attempt, max_known_community_teams)
        if team_type == "community":
            current_team_index = team_value
            custom_name = None
            current_team_info = f"Comunidad #{team_value + 1}"
        else:
            current_team_index = 0
            custom_name = team_value
            current_team_info = f"Propia {team_value}"

        phase_label = "Barrido" if is_fast_sweep else "Insistencia"
        current_team_display = f"{current_team_info} ({phase_label})"

        retry_enabled = getattr(config, "RETRY_EACH_FORMATION", True)
        effective_max_subs = 1 if (is_fast_sweep or not retry_enabled) else getattr(config, "SUBATTEMPTS_PER_FORMATION", 5)

        update_bot_stats(
            mode=current_mode,
            stage_attempt=stage_attempt + 1,
            sub_attempt=sub_attempt + 1,
            max_sub_attempts=effective_max_subs,
            team_info=current_team_display,
            defeats_consecutive=consecutive_defeats,
            stages_normal=stages_cleared_normal,
            stages_phantimal=stages_cleared_phantimal,
            stages_total=stages_cleared_normal + stages_cleared_phantimal,
            victories_session=victories_session,
            defeats_session=defeats_session,
            last_battle_duration=last_battle_duration
        )

        # 1. VERIFICAR VICTORIA
        _, victory_pt = match_template_single(screen_cv, "victory")
        if victory_pt:
            matched = True
            in_battle = False
            auto_verified_on = False
            if auto_was_disabled:
                print("[AUTO-SKILLS] ¡Victoria obtenida a pesar de que el auto-lanzamiento estuvo apagado al inicio!")
                auto_was_disabled = False
            if battle_start_time:
                last_battle_duration = f"{round(time.time() - battle_start_time, 1)}s"
                battle_start_time = None
            print(f"[VICTORIA] ¡Etapa superada con éxito! (Duración del combate: {last_battle_duration})")
            
            # Incrementar contadores de victorias de la sesión
            victories_session += 1
            if current_mode == "battle":
                stages_cleared_normal += 1
            else:
                stages_cleared_phantimal += 1
            print(f"[ESTADÍSTICAS] Superadas en esta sesión -> Normal: {stages_cleared_normal} | Phantimal: {stages_cleared_phantimal} (Total: {stages_cleared_normal + stages_cleared_phantimal})")
            
            # Resetear contadores de fallos y desbloquear modos
            current_team_index = 0
            consecutive_defeats = 0
            stage_attempt = 0
            sub_attempt = 0
            mode_locked = False
            team_already_copied = False
            current_displayed_team_index = 0
            max_known_community_teams = None  # Reiniciar descubrimiento de lista para el nuevo nivel
            
            update_bot_stats(
                battle_state="¡Victoria!",
                last_battle_duration=last_battle_duration,
                victories_session=victories_session,
                defeats_consecutive=0,
                stage_attempt=1,
                sub_attempt=1,
                stages_normal=stages_cleared_normal,
                stages_phantimal=stages_cleared_phantimal,
                stages_total=stages_cleared_normal + stages_cleared_phantimal
            )
            
            # Incrementar contador de batallas e intercalar si llegamos a 5 (solo si el modo no está bloqueado)
            battles_count += 1
            print(f"[BOT] Batalla completada en este modo ({battles_count}/5).")
            
            if battles_count >= 5 and not mode_locked:
                print("[MODO] Se han completado 5 batallas en este modo. Rotando al modo alternativo...")
                need_mode_switch = True
                battles_count = 0
                max_known_community_teams = None
                current_mode = "phantimal" if current_mode == "battle" else "battle"
                
                # Para cambiar de modo tras ganar, hacemos clic fuera del botón "continuar" (en el cartel de victoria).
                # Esto nos saca de forma nativa al selector general de etapas AFK.
                print("[BOT] Volviendo al mapa general para alternar modo...")
                simulate_human_click(window, victory_pt[0], victory_pt[1])
            else:
                need_mode_switch = False
                # Hacer clic en el botón de continuar según el modo activo
                btn_name = "continuar_normal" if current_mode == "battle" else "continuar_phantimal"
                _, cont_pt = match_template_single(screen_cv, btn_name)
                
                if cont_pt:
                    print(f"[BOT] Avanzando a la siguiente etapa ({btn_name})...")
                    simulate_human_click(window, cont_pt[0], cont_pt[1])
                else:
                    # Fallback: hacer clic en el centro de la pantalla
                    print("[BOT] Pantalla de victoria detectada pero no veo el botón de continuar. Clic en el centro de victoria.")
                    simulate_human_click(window, victory_pt[0], victory_pt[1])
                
            time.sleep(config.LOOP_DELAY + 0.8)
            continue
            
        # 2. VERIFICAR DERROTA
        _, defeat_pt = match_template_single(screen_cv, "defeat")
        if defeat_pt:
            matched = True
            in_battle = False
            auto_verified_on = False
            if battle_start_time:
                last_battle_duration = f"{round(time.time() - battle_start_time, 1)}s"
                battle_start_time = None
            current_displayed_team_index = 0  # El panel se cierra por la derrota, así que se reinicia a 0
            
            if auto_was_disabled:
                print(f"[AUTO-SKILLS] Derrota detectada tras reactivar auto-habilidades ({last_battle_duration}).")
                print("  -> REINTENTANDO la misma formación SIN CONTAR este intento ni sumar derrota.")
                auto_was_disabled = False
                team_already_copied = True  # Mantenemos el equipo puesto en el tablero
                
                update_bot_stats(
                    battle_state="Reintento Auto-Skills",
                    last_battle_duration=last_battle_duration
                )
            else:
                consecutive_defeats += 1
                defeats_session += 1
                
                # Lógica de subintentos por formación según fase (barrido rápido vs insistencia)
                if (sub_attempt + 1) < effective_max_subs:
                    sub_attempt += 1
                    team_already_copied = True  # La formación sigue colocada en el tablero, no hace falta reabrir menús
                    print(f"[DERROTA] Falla en la etapa. Reintentando formación (Subintento #{sub_attempt + 1}/{effective_max_subs} | Intento #{stage_attempt + 1}/20). (Derrotas globales consecutivas: {consecutive_defeats}/30)")
                else:
                    sub_attempt = 0
                    stage_attempt += 1
                    battles_count += 1
                    team_already_copied = False
                    phase_msg = "Fin de barrido para esta formación" if is_fast_sweep else "Subintentos agotados"
                    print(f"[DERROTA] Falla en la etapa ({phase_msg}). Pasando a la siguiente formación (Intento #{stage_attempt + 1}/20 en este nivel). (Derrotas globales consecutivas: {consecutive_defeats}/30)")
                
                update_bot_stats(
                    battle_state="Derrota",
                    last_battle_duration=last_battle_duration,
                    defeats_session=defeats_session,
                    defeats_consecutive=consecutive_defeats,
                    stage_attempt=stage_attempt + 1,
                    sub_attempt=sub_attempt + 1
                )
                
                # Failsafe para detener si acumulamos 30 derrotas consecutivas globales sin victoria
                if consecutive_defeats >= 30:
                    print("\n" + "="*60)
                    print("[FAILSAFE] SE HAN SUCEDIDO 30 DERROTAS CONSECUTIVAS GLOBALES.")
                    print("Es probable que tus personajes necesiten subir de nivel en la Resonancia.")
                    if getattr(config, "SHUTDOWN_ON_30_DEFEATS", False):
                        print("[FAILSAFE] APAGANDO EL ORDENADOR EN 60 SEGUNDOS...")
                        print("="*60 + "\n")
                        os.system("shutdown /s /t 60")
                    else:
                        print("Deteniendo el bot para evitar un bucle infinito.")
                        print("="*60 + "\n")
                    raise RuntimeError("Límite de 30 derrotas consecutivas globales alcanzado.")
                
                # Comprobar si debemos alternar de modo por límite de 20 intentos en la misma etapa
                if stage_attempt >= 20:
                    print("[MODO] Se han realizado 20 intentos fallidos en este nivel. Cambiando al otro modo y bloqueándolo allí...")
                    need_mode_switch = True
                    current_mode = "phantimal" if current_mode == "battle" else "battle"
                    mode_locked = True
                    stage_attempt = 0
                    sub_attempt = 0
                    battles_count = 0
                    current_team_index = 0
                    team_already_copied = False
                    max_known_community_teams = None
                # Comprobar si debemos alternar por límite de 5 formaciones (solo si el modo no está bloqueado)
                elif battles_count >= 5 and not mode_locked:
                    print("[MODO] Se han completado 5 formaciones en este modo. Rotando al modo alternativo...")
                    need_mode_switch = True
                    battles_count = 0
                    current_team_index = 0
                    stage_attempt = 0
                    sub_attempt = 0
                    team_already_copied = False
                    max_known_community_teams = None
                    current_mode = "phantimal" if current_mode == "battle" else "battle"
                else:
                    next_type, next_value, next_sweep = get_team_for_attempt(stage_attempt, max_known_community_teams)
                    next_phase = "Barrido Rápido" if next_sweep else "Insistencia"
                    next_subs = 1 if (next_sweep or not retry_enabled) else getattr(config, "SUBATTEMPTS_PER_FORMATION", 5)
                    if next_type == "community":
                        print(f"[BOT] Siguiente formación: Comunidad #{next_value + 1} [{next_phase}] (Subintento #{sub_attempt + 1}/{next_subs})")
                    else:
                        print(f"[BOT] Siguiente formación: Personalizada {next_value} [{next_phase}] (Subintento #{sub_attempt + 1}/{next_subs})")
                
            # Buscar el botón de reintentar
            _, retry_pt = match_template_single(screen_cv, "retry")
            if retry_pt:
                if need_mode_switch:
                    # En lugar de reintentar el combate, queremos salir para cambiar de pestaña.
                    # Buscamos el botón de retroceso (atrás) para volver al menú de selección
                    _, atras_pt = match_template_single(screen_cv, "atras")
                    if atras_pt:
                        print("[BOT] Retrocediendo al menú principal de etapas para cambiar de pestaña...")
                        simulate_human_click(window, atras_pt[0], atras_pt[1])
                    else:
                        # Si no hay atrás en la pantalla de derrota, pulsamos retry y luego saldremos
                        print("[BOT] Volviendo a preparación para poder retroceder...")
                        simulate_human_click(window, retry_pt[0], retry_pt[1])
                else:
                    print("[BOT] Volviendo a preparación para reintentar...")
                    simulate_human_click(window, retry_pt[0], retry_pt[1])
            else:
                # Si no encuentra el botón de reintentar pero ve derrota, clic en el texto para cerrar
                simulate_human_click(window, defeat_pt[0], defeat_pt[1])
                
            time.sleep(config.LOOP_DELAY + 0.8)
            continue
            
        # 2.2. VERIFICACIÓN DE AUTO-LANZAMIENTO DE HABILIDADES DURANTE EL COMBATE
        if in_battle and not auto_verified_on:
            auto_status, auto_pt = check_auto_skills_status(screen_cv)
            if auto_status == "OFF":
                matched = True
                print("[AUTO-SKILLS] ¡ALERTA! El lanzamiento automático de habilidades está DESACTIVADO (icono gris).")
                print("  -> Haciendo clic en el icono para activarlo...")
                simulate_human_click(window, auto_pt[0], auto_pt[1])
                auto_was_disabled = True
                time.sleep(0.4)
                continue
            elif auto_status == "ON":
                if auto_was_disabled:
                    print("[AUTO-SKILLS] Activación confirmada (icono dorado). Si la partida se pierde, se reintentará sin contar el intento.")
                elif config.DEBUG:
                    print("[AUTO-SKILLS] Lanzamiento automático de habilidades verificado (ACTIVADO).")
                auto_verified_on = True
            
        # 2.5. VERIFICAR HÉROE NO DISPONIBLE (Falta personaje en la formación copiada)
        _, no_hero_pt = match_template_single(screen_cv, "cancel_no-heroe")
        if no_hero_pt:
            matched = True
            print("[ADVERTENCIA] La formación copiada contiene héroes no disponibles en tu cuenta.")
            print("[BOT] Haciendo clic en Cancelar para buscar otra formación...")
            simulate_human_click(window, no_hero_pt[0], no_hero_pt[1])
            
            # Avanzar al siguiente intento para el próximo ciclo
            sub_attempt = 0
            stage_attempt += 1
            battles_count += 1
            team_already_copied = False
            
            update_bot_stats(
                battle_state="Héroe Faltante",
                stage_attempt=stage_attempt + 1,
                sub_attempt=1
            )
            
            # Comprobar si debemos alternar de modo por límite de 20 intentos en la misma etapa
            if stage_attempt >= 20:
                print("[MODO] Se han realizado 20 intentos en este nivel (incluyendo cancelaciones). Cambiando al otro modo y bloqueándolo allí...")
                need_mode_switch = True
                current_mode = "phantimal" if current_mode == "battle" else "battle"
                mode_locked = True
                stage_attempt = 0
                battles_count = 0
                current_team_index = 0
                max_known_community_teams = None
            else:
                next_type, next_value, next_sweep = get_team_for_attempt(stage_attempt, max_known_community_teams)
                next_phase = "Barrido Rápido" if next_sweep else "Insistencia"
                if next_type == "community":
                    print(f"[BOT] Siguiente intento configurado para usar formación de comunidad #{next_value + 1} [{next_phase}]")
                else:
                    print(f"[BOT] Siguiente intento configurado para usar formación personalizada: {next_value} [{next_phase}]")
                
            time.sleep(config.LOOP_DELAY + 0.5)
            continue
                
            time.sleep(config.LOOP_DELAY + 0.5)
            continue
            
        # 2.7. VERIFICAR ADVERTENCIA DE RECOMPENSAS LIMITADAS (Tick verde)
        _, green_tick_pt = match_template_single(screen_cv, "green_tick")
        if green_tick_pt:
            matched = True
            print("[BOT] Detectado popup de advertencia de recompensas limitadas. Confirmando...")
            simulate_human_click(window, green_tick_pt[0], green_tick_pt[1])
            time.sleep(config.LOOP_DELAY + 0.6)
            continue
            
        # 3. CAMBIO DE MODO REQUERIDO (Atascado en un modo, volver al mapa principal de etapas)
        if need_mode_switch:
            _, battle_prep_pt = match_template_single(screen_cv, "battle")
            _, copy_prep_pt = match_template_single(screen_cv, "copy")
            _, use_prep_pt = match_template_single(screen_cv, "use_btn")
            
            if battle_prep_pt or copy_prep_pt or use_prep_pt:
                matched = True
                
                # Si el panel de registros está abierto, primero debemos cerrarlo para ver el botón de atrás
                if copy_prep_pt or use_prep_pt:
                    print("[BOT] Panel de registros abierto durante solicitud de cambio de modo. Cerrando panel...")
                    simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                    time.sleep(0.6)
                    continue
                    
                # Si el panel está cerrado, buscamos el botón de retroceso (atrás)
                _, atras_pt = match_template_single(screen_cv, "atras")
                if atras_pt:
                    print("[BOT] Saliendo de la pantalla de preparación para alternar modo...")
                    simulate_human_click(window, atras_pt[0], atras_pt[1])
                    time.sleep(config.LOOP_DELAY + 0.5)
                    continue
                    
        # 4. PANTALLA DE PREPARACIÓN DEL COMBATE
        # Sabemos que estamos aquí si vemos el botón verde 'battle' o si el panel ya está abierto ('copy')
        _, battle_pt = match_template_single(screen_cv, "battle")
        _, copy_pt = match_template_single(screen_cv, "copy")
        _, use_pt = match_template_single(screen_cv, "use_btn")
        if (battle_pt or copy_pt or use_pt) and not need_mode_switch:
            matched = True
            
            # Si ya hemos copiado el equipo en esta fase, iniciamos combate directamente
            if team_already_copied:
                if battle_pt:
                    if team_type == "community":
                        print(f"[BOT] Equipo ya configurado. Iniciando la batalla (Intento #{stage_attempt + 1} | Subintento #{sub_attempt + 1} en esta etapa)...")
                    else:
                        print(f"[BOT] Equipo ya configurado. Iniciando la batalla (Intento con formación personalizada {custom_name} | Subintento #{sub_attempt + 1})...")
                    simulate_human_click(window, battle_pt[0], battle_pt[1])
                    in_battle = True
                    auto_verified_on = False
                    battle_start_time = time.time()
                    no_match_count = 0
                    update_bot_stats(battle_state="En Batalla")
                    time.sleep(config.LOOP_DELAY + 1.0)
                else:
                    print("[ADVERTENCIA] Intentando iniciar batalla pero el botón 'battle' no es visible.")
                    # Si por alguna razón el panel se cerró mal, reintentamos el proceso de copiado en el siguiente ciclo
                    team_already_copied = False
                continue
            
            if team_type == "custom":
                # LÓGICA DE FORMACIONES PERSONALIZADAS
                if copy_pt:
                    print("[RECORDS] El panel de comunidad está abierto pero toca usar formación personalizada. Cerrándolo...")
                    simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                    current_displayed_team_index = 0
                    time.sleep(0.6)
                    continue
                    
                form_panel_open = (use_pt is not None)
                if not form_panel_open:
                    # El panel de formaciones está cerrado. Buscamos el botón para abrirlo
                    _, form_btn_pt = match_template_single(screen_cv, "formations_btn")
                    if form_btn_pt:
                        print("[FORMACIONES] Abriendo el panel de formaciones personalizadas...")
                        simulate_human_click(window, form_btn_pt[0], form_btn_pt[1])
                        time.sleep(config.LOOP_DELAY + 0.5)
                    else:
                        print("[ADVERTENCIA] Botón de formaciones personalizadas no encontrado.")
                    continue
                else:
                    # El panel de formaciones personalizadas está abierto.
                    # Buscar la cabecera correspondiente (AFKST1 o AFKST2)
                    _, target_header_pt = match_template_single(screen_cv, custom_name)
                    if target_header_pt:
                        print(f"[FORMACIONES] Encontrada cabecera para {custom_name} en Y: {target_header_pt[1]}")
                        # Buscar todos los botones "Use" en la pantalla
                        use_points = match_template_multi(screen_cv, "use_btn")
                        if use_points:
                            # Encontrar el botón "Use" más alineado verticalmente con target_header_pt[1]
                            best_use_pt = min(use_points, key=lambda pt: abs(pt[1] - target_header_pt[1]))
                            if abs(best_use_pt[1] - target_header_pt[1]) < 40:
                                print(f"[FORMACIONES] Aplicando formación {custom_name} haciendo clic en Use en Y: {best_use_pt[1]}")
                                simulate_human_click(window, best_use_pt[0], best_use_pt[1])
                                team_already_copied = True
                                time.sleep(config.LOOP_DELAY + 0.8)
                            else:
                                print(f"[ADVERTENCIA] Botón 'Use' más cercano a {custom_name} está muy desalineado ({abs(best_use_pt[1] - target_header_pt[1])}px).")
                        else:
                            print("[ADVERTENCIA] No se encontraron botones 'Use' en el panel de formaciones.")
                    else:
                        print(f"[ADVERTENCIA] No se encontró la formación personalizada {custom_name} en pantalla.")
                        # Cerrar el panel haciendo clic en la parte izquierda para no bloquearse
                        simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                        time.sleep(0.5)
                    continue
            else:
                # LÓGICA DE FORMACIONES DE LA COMUNIDAD (Copiado clásico)
                if use_pt:
                    # Si el panel de formaciones personalizadas está abierto por error, lo cerramos
                    print("[FORMACIONES] Cerrando panel de formaciones personalizadas para usar comunidad...")
                    simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                    time.sleep(0.5)
                    continue
                    
                if not copy_pt:
                    # El menú de récords está cerrado. Buscamos el botón para abrirlo
                    _, record_pt = match_template_single(screen_cv, "records")
                    if record_pt:
                        print("[BOT] Abriendo el panel de formaciones de la comunidad...")
                        simulate_human_click(window, record_pt[0], record_pt[1])
                        current_displayed_team_index = 0  # Restablecer puesto que se abre desde cero
                        time.sleep(config.LOOP_DELAY + 0.4)
                    else:
                        # Si no encuentra el botón de registros, empezamos combate con lo que haya
                        print("[ADVERTENCIA] Botón de registros no encontrado. Iniciando combate por defecto...")
                        if battle_pt:
                            simulate_human_click(window, battle_pt[0], battle_pt[1])
                            in_battle = True
                            auto_verified_on = False
                            battle_start_time = time.time()
                            no_match_count = 0
                            update_bot_stats(battle_state="En Batalla")
                            time.sleep(config.LOOP_DELAY + 0.8)
                    continue
                else:
                    # El panel de registros está abierto.
                    # Calcular cuántos clics de avance necesitamos desde la posición actual en pantalla
                    clicks_needed = current_team_index - current_displayed_team_index
                    if clicks_needed < 0:
                        print(f"[RECORDS] La formación objetivo #{current_team_index + 1} requiere retroceder (actual: #{current_displayed_team_index + 1}). Cerrando panel para reiniciar...")
                        # Hacer clic en la parte izquierda del juego para cerrar el panel deslizante
                        simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                        current_displayed_team_index = 0
                        time.sleep(0.6)
                        continue
                        
                    if clicks_needed > 0:
                        print(f"[RECORDS] Avanzando {clicks_needed} veces para llegar a la formación #{current_team_index + 1} (Índice actual: #{current_displayed_team_index + 1})...")
                        
                        advanced_ok = True
                        for i in range(clicks_needed):
                            # En el primer paso usamos la captura screen_cv, en los siguientes refrescamos para verificar que la flechita siga visible
                            if i > 0:
                                time.sleep(0.4)
                                try:
                                    fresh_s = ImageGrab.grab(bbox=bbox, all_screens=True)
                                    fresh_s_cv = cv2.cvtColor(np.array(fresh_s), cv2.COLOR_RGB2BGR)
                                    _, step_next_pt = match_template_single(fresh_s_cv, "next_formation")
                                except:
                                    step_next_pt = None
                            else:
                                _, step_next_pt = match_template_single(screen_cv, "next_formation")
                                
                            if not step_next_pt:
                                max_known_community_teams = current_displayed_team_index + 1
                                print(f"[RECORDS] Fin de lista detectado. No hay botón de siguiente formación tras el equipo #{current_displayed_team_index + 1} (Tope comunitario en esta etapa: {max_known_community_teams}).")
                                advanced_ok = False
                                break
                                
                            print(f"  -> Clic en Siguiente Formación ({i+1}/{clicks_needed})")
                            simulate_human_click(window, step_next_pt[0], step_next_pt[1])
                            current_displayed_team_index += 1
                            
                        if not advanced_ok:
                            # Cerramos el panel de registros para avanzar al siguiente paso disponible
                            print("[RECORDS] Cerrando panel de comunidad para saltar al siguiente equipo disponible...")
                            simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                            current_displayed_team_index = 0
                            stage_attempt += 1
                            sub_attempt = 0
                            team_already_copied = False
                            time.sleep(0.6)
                            
                            if stage_attempt >= 20:
                                print("[MODO] Se han realizado 20 intentos en este nivel. Cambiando al otro modo y bloqueándolo allí...")
                                need_mode_switch = True
                                current_mode = "phantimal" if current_mode == "battle" else "battle"
                                mode_locked = True
                                stage_attempt = 0
                                sub_attempt = 0
                                battles_count = 0
                                current_team_index = 0
                                team_already_copied = False
                                max_known_community_teams = None
                                _, atras_pt = match_template_single(screen_cv, "atras")
                                if atras_pt:
                                    simulate_human_click(window, atras_pt[0], atras_pt[1])
                                time.sleep(config.LOOP_DELAY + 0.5)
                            continue
                        
                # Volver a buscar el botón 'copy' actualizado en pantalla y pulsarlo
                # Capturamos de nuevo para seguridad de coordenadas
                try:
                    new_screen = ImageGrab.grab(bbox=bbox, all_screens=True)
                    new_screen_cv = cv2.cvtColor(np.array(new_screen), cv2.COLOR_RGB2BGR)
                    _, fresh_copy_pt = match_template_single(new_screen_cv, "copy")
                except:
                    fresh_copy_pt = copy_pt
                    
                if fresh_copy_pt:
                    print(f"[BOT] Copiando formación seleccionada (Índice: {current_team_index})...")
                    simulate_human_click(window, fresh_copy_pt[0], fresh_copy_pt[1])
                    team_already_copied = True
                    time.sleep(0.9) # Espera para aplicar héroes y que se cierre el panel
                    
                continue
                
        # 5. MENÚ DE SELECCIÓN DE ETAPAS AFK (Phantimal vs Normal Battle)
        # Identificar si estamos en este menú buscando los botones challenge correspondientes
        _, normal_chall_pt = match_template_single(screen_cv, "normal_challenge")
        _, phant_chall_pt = match_template_single(screen_cv, "phantimal_challenge")
        
        if normal_chall_pt or phant_chall_pt:
            matched = True
            in_battle = False
            auto_verified_on = False
            auto_was_disabled = False
            # Si estamos aquí, podemos apagar la bandera de cambio de modo ya que estamos en el selector
            need_mode_switch = False
            
            # Detectar si uno de los modos ya no está disponible (completado o no desbloqueado)
            if normal_chall_pt and not phant_chall_pt:
                if not mode_locked or current_mode != "battle":
                    print("[MODO] Detectado que solo el modo BATTLE NORMAL está disponible (Phantimal completado o ausente). Bloqueando bot en modo Battle.")
                    current_mode = "battle"
                    mode_locked = True
            elif phant_chall_pt and not normal_chall_pt:
                if not mode_locked or current_mode != "phantimal":
                    print("[MODO] Detectado que solo el modo PHANTIMAL CHALLENGE está disponible (Battle completado o ausente). Bloqueando bot en modo Phantimal.")
                    current_mode = "phantimal"
                    mode_locked = True
            
            if current_mode == "battle" and normal_chall_pt:
                print("[BOT] Seleccionando modo BATTLE NORMAL...")
                simulate_human_click(window, normal_chall_pt[0], normal_chall_pt[1])
            elif current_mode == "phantimal" and phant_chall_pt:
                print("[BOT] Seleccionando modo PHANTIMAL CHALLENGE...")
                simulate_human_click(window, phant_chall_pt[0], phant_chall_pt[1])
            else:
                # Si el otro modo está bloqueado por atasco/fin de lista, no podemos usar fallback hacia él
                if mode_locked:
                    print("\n" + "="*60)
                    print("[BLOQUEO] ALCANZADO EL FIN DE LA LISTA Y EL OTRO MODO NO ESTÁ DISPONIBLE.")
                    print("El modo alternativo solicitado no se encuentra visible y el actual está bloqueado.")
                    print("Deteniendo el bot para evitar un bucle de entrada/salida infinito.")
                    print("="*60 + "\n")
                    raise RuntimeError("Ambos modos de juego están bloqueados o el modo alternativo es inaccesible.")
                
                # Si no está bloqueado, hacemos fallback normal
                fallback_pt = normal_chall_pt if normal_chall_pt else phant_chall_pt
                print(f"[BOT] Entrando a la etapa disponible...")
                simulate_human_click(window, fallback_pt[0], fallback_pt[1])
                
            time.sleep(config.LOOP_DELAY + 0.8)
            continue
                
        # 6. ENTRADA GENERAL DESDE EL MENÚ DE INICIO / NAVEGACIÓN
        # Si vemos 'AFK_stages' en el menú de modos, hacemos clic
        _, stages_pt = match_template_single(screen_cv, "AFK_stages")
        if stages_pt:
            matched = True
            print("[BOT] Entrando a AFK Stages...")
            simulate_human_click(window, stages_pt[0], stages_pt[1])
            time.sleep(config.LOOP_DELAY + 0.4)
            continue
            
        # Si estamos en el lobby principal y vemos 'battle_modes', hacemos clic
        _, modes_pt = match_template_single(screen_cv, "battle_modes")
        if modes_pt:
            matched = True
            print("[BOT] Entrando al menú de Modos de Batalla...")
            simulate_human_click(window, modes_pt[0], modes_pt[1])
            time.sleep(config.LOOP_DELAY + 0.4)
            continue
            
        # 7. SOPORTE DE POPUPS GENERALES / CERRAR RECOMPENSAS
        _, cerrar_pt = match_template_single(screen_cv, "cerrar")
        if cerrar_pt and not battle_pt:
            matched = True
            print("[BOT] Cerrando popup detectado en pantalla...")
            simulate_human_click(window, cerrar_pt[0], cerrar_pt[1])
            time.sleep(config.LOOP_DELAY)
            continue
            
        _, tap_exit_pt = match_template_single(screen_cv, "tap_to_exit")
        if tap_exit_pt:
            matched = True
            print("[BOT] Cerrando pantalla mediante 'Tap to exit'...")
            simulate_human_click(window, tap_exit_pt[0], tap_exit_pt[1])
            time.sleep(config.LOOP_DELAY + 0.5)
            continue
            
        # Espera pasiva del bucle si no hay coincidencias
        if not matched:
            no_match_count += 1
            
            # Lógica de clic de escape seguro para popups/banners persistentes de las 2 AM
            # IMPORTANTE: Desactivado durante el combate para no alterar AUTO ni abrir pausas
            if not in_battle and no_match_count >= 15 and no_match_count % 10 == 0:
                print(f"[BOT] Alerta: {no_match_count} ciclos sin coincidencias. Intentando clic de escape seguro...")
                # Clic en la zona muerta media-izquierda (15% ancho, 50% alto) para cerrar posibles diálogos
                simulate_human_click(window, int(window.width * 0.15), int(window.height * 0.5))
                time.sleep(config.LOOP_DELAY + 0.5)
                continue # Volver a capturar inmediatamente
                
            if no_match_count % 5 == 0:
                print(f"[INFO] Buscando coincidencias... (Ciclo {no_match_count} sin clics)")
                if config.DEBUG:
                    scores = []
                    # Mostrar el puntaje de coincidencia de las plantillas más representativas
                    for name in ["battle_modes", "AFK_stages", "battle", "victory", "defeat", "copy", "records", "next_formation"]:
                        conf, _ = match_template_single(screen_cv, name)
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
