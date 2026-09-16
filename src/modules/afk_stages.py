import os
import random
import time

import cv2
import numpy as np
import yaml
from PIL import ImageGrab

import config
from src.core.inputs import simulate_human_click
from src.core.vision import (
    check_auto_skills_status,
    load_template,
    load_templates_spec,
    match_template_multi,
    match_template_single,
)
from src.core.window import get_game_window, standardize_window_size

# Cargar especificaciones de estrategia
STRATEGY_SPEC_PATH = os.path.join(config.BASE_DIR, "specs", "battle_strategy.yaml")

def load_battle_strategy_spec():
    if os.path.exists(STRATEGY_SPEC_PATH):
        try:
            with open(STRATEGY_SPEC_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

STRATEGY_SPEC = load_battle_strategy_spec()

def get_team_for_attempt(stage_attempt, max_known_community=None):
    """
    Calcula el tipo de equipo, su valor/índice y si pertenece a la Fase 1 (barrido rápido)
    o a la Fase 2 (insistencia con subintentos).
    Retorna (team_type, team_value, is_fast_sweep)
    """
    use_custom = getattr(config, "USE_CUSTOM_FORMATIONS", True)
    max_teams = max_known_community if (max_known_community is not None and max_known_community > 0) else 10

    # 1. FASE 1: BARRIDO RÁPIDO (1 intento por formación para victoria rápida)
    fast_sweep_steps = []
    
    odds = STRATEGY_SPEC.get("fast_sweep", {}).get("community_odds", [0, 2, 4, 6, 8])
    for idx in odds:
        if idx < max_teams:
            fast_sweep_steps.append(("community", idx, True))
            
    evens = STRATEGY_SPEC.get("fast_sweep", {}).get("community_evens", [1, 3, 5, 7])
    for idx in evens:
        if idx < max_teams:
            fast_sweep_steps.append(("community", idx, True))
            
    if use_custom:
        custom_teams = STRATEGY_SPEC.get("fast_sweep", {}).get("custom_teams", ["AFKST1", "AFKST2"])
        for cteam in custom_teams:
            fast_sweep_steps.append(("custom", cteam, True))

    # 2. FASE 2: INSISTENCIA POR RNG (aplica los subintentos configurados en el slider)
    insist_steps = []
    
    primary = STRATEGY_SPEC.get("insistence", {}).get("primary_community", [0])
    for idx in primary:
        if idx < max_teams:
            insist_steps.append(("community", idx, False))
        
    if use_custom:
        insist_custom = STRATEGY_SPEC.get("insistence", {}).get("custom_teams", ["AFKST1", "AFKST2"])
        for cteam in insist_custom:
            insist_steps.append(("custom", cteam, False))
        
    secondary = STRATEGY_SPEC.get("insistence", {}).get("secondary_community", [1, 2])
    for idx in secondary:
        if idx < max_teams:
            insist_steps.append(("community", idx, False))
            
    fallback = STRATEGY_SPEC.get("insistence", {}).get("fallback_community", [3, 4])
    for idx in fallback:
        if idx < max_teams:
            insist_steps.append(("community", idx, False))

    all_steps = fast_sweep_steps + insist_steps
    if not all_steps:
        return "community", 0, False

    if stage_attempt < len(all_steps):
        return all_steps[stage_attempt]
    else:
        pool = insist_steps if insist_steps else all_steps
        fallback_idx = (stage_attempt - len(all_steps)) % len(pool)
        return pool[fallback_idx]

def update_bot_stats(mode=None, stage_attempt=None, sub_attempt=None, max_sub_attempts=None,
                     team_info=None, battle_state=None, last_battle_duration=None,
                     victories_session=None, defeats_session=None, defeats_consecutive=None,
                     stages_normal=None, stages_phantimal=None, stages_total=None):
    """Actualiza de forma segura el diccionario global BOT_STATS para la GUI en tiempo real."""
    stats = getattr(config, "BOT_STATS", None)
    updates = {
        "mode": mode,
        "stage_attempt": stage_attempt,
        "sub_attempt": sub_attempt,
        "max_sub_attempts": max_sub_attempts,
        "team_info": team_info,
        "battle_state": battle_state,
        "last_battle_duration": str(last_battle_duration) if last_battle_duration is not None else None,
        "victories_session": victories_session,
        "defeats_session": defeats_session,
        "defeats_consecutive": defeats_consecutive,
        "stages_normal": stages_normal,
        "stages_phantimal": stages_phantimal,
        "stages_total": stages_total,
    }
    for k, v in updates.items():
        if v is not None:
            stats[k] = v


def run_afk_stages():
    """Bucle principal de ejecución del módulo de etapas AFK."""
    print("=" * 60)
    print("        BOT PERSONALIZADO DE AFK JOURNEY (FASES AFK)")
    print("=" * 60)
    print("Lógica activa:")
    print(" - Copiado de equipos 1 al 5 secuencialmente por intento.")
    print(" - Alterna modos (Battle <-> Phantimal) en caso de bloqueo.")
    print(" Failsafe: Mueve el ratón a la esquina superior izquierda para detener.")
    print(" Parar: Presiona Ctrl+C en esta ventana.")
    print("-" * 60)
    
    # Comprobación de plantillas visuales
    spec_dict = load_templates_spec()
    essential_templates = list(spec_dict.keys()) if spec_dict else [
        "battle_modes", "AFK_stages", "normal_challenge", "phantimal_challenge",
        "records", "next_formation", "copy", "battle", "victory",
        "continuar_normal", "continuar_phantimal", "defeat", "retry", "atras",
        "cancel_no-heroe", "formations_btn", "AFKST1", "AFKST2", "use_btn", "green_tick",
        "tap_to_exit", "auto_off", "auto_on", "all_stages_cleared"
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
        
    current_team_index = 0
    consecutive_defeats = 0
    need_mode_switch = False
    connected_window_title = None
    no_match_count = 0
    team_already_copied = False
    battles_count = 0
    stages_cleared_normal = 0
    stages_cleared_phantimal = 0
    stage_attempt = 0
    sub_attempt = 0
    max_known_community_teams = None
    mode_locked = False
    current_displayed_team_index = 0
    team_type = "community"
    custom_name = None
    in_battle = False
    auto_verified_on = False
    auto_was_disabled = False
    battle_start_time = None
    last_battle_duration = "0.0s"
    victories_session = 0
    defeats_session = 0
    
    print(f"\n[ESTADO INICIAL] Modo de inicio: {current_mode.upper()} | Equipo inicial: #{current_team_index + 1}")
    
    while True:
        if not getattr(config, "BOT_RUNNING", True):
            print("[BOT] Detención solicitada. Saliendo de la ejecución...")
            break

        matched = False
        window = get_game_window()
        if not window:
            print("[ADVERTENCIA] No se detecta la ventana del juego. Asegúrate de tenerlo abierto y no minimizado.")
            for _ in range(6):
                if not getattr(config, "BOT_RUNNING", True):
                    break
                time.sleep(0.5)
            continue
            
        if window.title != connected_window_title:
            connected_window_title = window.title
            print(f"[OK] Conectado a la ventana del juego: '{window.title}' (Posición: {window.left},{window.top} | Tamaño: {window.width}x{window.height})")
            window = standardize_window_size(window)

        bbox = (window.left, window.top, window.left + window.width, window.top + window.height)
        try:
            screenshot = ImageGrab.grab(bbox=bbox, all_screens=True)
            screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        except Exception as e:
            if getattr(config, "DEBUG", False):
                print(f"[ERROR] Error al realizar captura de pantalla: {e}")
            time.sleep(2)
            continue
            
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
            
            victories_session += 1
            if current_mode == "battle":
                stages_cleared_normal += 1
            else:
                stages_cleared_phantimal += 1
            print(f"[ESTADÍSTICAS] Superadas en esta sesión -> Normal: {stages_cleared_normal} | Phantimal: {stages_cleared_phantimal} (Total: {stages_cleared_normal + stages_cleared_phantimal})")
            
            current_team_index = 0
            consecutive_defeats = 0
            stage_attempt = 0
            sub_attempt = 0
            mode_locked = False
            team_already_copied = False
            current_displayed_team_index = 0
            max_known_community_teams = None
            
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
            
            battles_count += 1
            print(f"[BOT] Batalla completada en este modo ({battles_count}/5).")
            
            if battles_count >= 5 and not mode_locked:
                print("[MODO] Se han completado 5 batallas en este modo. Rotando al modo alternativo...")
                need_mode_switch = True
                battles_count = 0
                max_known_community_teams = None
                current_mode = "phantimal" if current_mode == "battle" else "battle"
                
                print("[BOT] Volviendo al mapa general para alternar modo...")
                simulate_human_click(window, victory_pt[0], victory_pt[1])
            else:
                need_mode_switch = False
                btn_name = "continuar_normal" if current_mode == "battle" else "continuar_phantimal"
                _, cont_pt = match_template_single(screen_cv, btn_name)
                
                if cont_pt:
                    print(f"[BOT] Avanzando a la siguiente etapa ({btn_name})...")
                    simulate_human_click(window, cont_pt[0], cont_pt[1])
                else:
                    print("[BOT] Pantalla de victoria detectada pero no veo el botón de continuar. Clic en el centro de victoria.")
                    simulate_human_click(window, victory_pt[0], victory_pt[1])
                
            time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.8)
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
            current_displayed_team_index = 0
            
            if auto_was_disabled:
                print(f"[AUTO-SKILLS] Derrota detectada tras reactivar auto-habilidades ({last_battle_duration}).")
                print("  -> REINTENTANDO la misma formación SIN CONTAR este intento ni sumar derrota.")
                auto_was_disabled = False
                team_already_copied = True
                
                update_bot_stats(
                    battle_state="Reintento Auto-Skills",
                    last_battle_duration=last_battle_duration
                )
            else:
                consecutive_defeats += 1
                defeats_session += 1
                
                if (sub_attempt + 1) < effective_max_subs:
                    sub_attempt += 1
                    team_already_copied = True
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
                
                max_consec = STRATEGY_SPEC.get("limits", {}).get("max_consecutive_defeats", 30)
                if consecutive_defeats >= max_consec:
                    print("\n" + "="*60)
                    print(f"[FAILSAFE] SE HAN SUCEDIDO {max_consec} DERROTAS CONSECUTIVAS GLOBALES.")
                    print("Es probable que tus personajes necesiten subir de nivel en la Resonancia.")
                    if getattr(config, "SHUTDOWN_ON_30_DEFEATS", False):
                        print("[FAILSAFE] APAGANDO EL ORDENADOR EN 60 SEGUNDOS...")
                        print("="*60 + "\n")
                        os.system("shutdown /s /t 60")
                    else:
                        print("Deteniendo el bot para evitar un bucle infinito.")
                        print("="*60 + "\n")
                    raise RuntimeError(f"Límite de {max_consec} derrotas consecutivas globales alcanzado.")
                
                max_stage_att = STRATEGY_SPEC.get("limits", {}).get("max_stage_attempts", 20)
                if stage_attempt >= max_stage_att:
                    print(f"[MODO] Se han realizado {max_stage_att} intentos fallidos en este nivel. Cambiando al otro modo y bloqueándolo allí...")
                    need_mode_switch = True
                    current_mode = "phantimal" if current_mode == "battle" else "battle"
                    mode_locked = True
                    stage_attempt = 0
                    sub_attempt = 0
                    battles_count = 0
                    current_team_index = 0
                    team_already_copied = False
                    max_known_community_teams = None
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
                
            _, retry_pt = match_template_single(screen_cv, "retry")
            if retry_pt:
                if need_mode_switch:
                    _, atras_pt = match_template_single(screen_cv, "atras")
                    if atras_pt:
                        print("[BOT] Retrocediendo al menú principal de etapas para cambiar de pestaña...")
                        simulate_human_click(window, atras_pt[0], atras_pt[1])
                    else:
                        print("[BOT] Volviendo a preparación para poder retroceder...")
                        simulate_human_click(window, retry_pt[0], retry_pt[1])
                else:
                    print("[BOT] Volviendo a preparación para reintentar...")
                    simulate_human_click(window, retry_pt[0], retry_pt[1])
            else:
                simulate_human_click(window, defeat_pt[0], defeat_pt[1])
                
            time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.8)
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
                elif getattr(config, "DEBUG", False):
                    print("[AUTO-SKILLS] Lanzamiento automático de habilidades verificado (ACTIVADO).")
                auto_verified_on = True
            
        # 2.5. VERIFICAR HÉROE NO DISPONIBLE
        _, no_hero_pt = match_template_single(screen_cv, "cancel_no-heroe")
        if no_hero_pt:
            matched = True
            print("[ADVERTENCIA] La formación copiada contiene héroes no disponibles en tu cuenta.")
            print("[BOT] Haciendo clic en Cancelar para buscar otra formación...")
            simulate_human_click(window, no_hero_pt[0], no_hero_pt[1])
            
            sub_attempt = 0
            stage_attempt += 1
            battles_count += 1
            team_already_copied = False
            
            update_bot_stats(
                battle_state="Héroe Faltante",
                stage_attempt=stage_attempt + 1,
                sub_attempt=1
            )
            
            max_stage_att = STRATEGY_SPEC.get("limits", {}).get("max_stage_attempts", 20)
            if stage_attempt >= max_stage_att:
                print(f"[MODO] Se han realizado {max_stage_att} intentos en este nivel (incluyendo cancelaciones). Cambiando al otro modo y bloqueándolo allí...")
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
                
            time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.5)
            continue
            
        # 2.7. VERIFICAR ADVERTENCIA DE RECOMPENSAS LIMITADAS (Tick verde)
        _, green_tick_pt = match_template_single(screen_cv, "green_tick")
        if green_tick_pt:
            matched = True
            print("[BOT] Detectado popup de advertencia de recompensas limitadas. Confirmando...")
            simulate_human_click(window, green_tick_pt[0], green_tick_pt[1])
            time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.6)
            continue

        # 2.8. VERIFICAR SI SE HAN SUPERADO TODAS LAS ETAPAS ("All Stages Cleared")
        if not in_battle:
            _, all_cleared_pt = match_template_single(screen_cv, "all_stages_cleared")
            if all_cleared_pt:
                matched = True
                print("\n" + "=" * 65)
                print("   🎉🎉🎉 ¡ENHORABUENA! HAS COMPLETADO TODAS LAS ETAPAS 🎉🎉🎉")
                print("=" * 65)
                print("[BOT] Se ha detectado el cartel 'All Stages Cleared' en pantalla.")
                print("[BOT] ¡Felicidades! Has superado todas las etapas disponibles de AFK Stages.")
                print("[BOT] Deteniendo el bot de forma segura para no consumir recursos.")
                print("=" * 65 + "\n")
                
                update_bot_stats(
                    battle_state="¡Todas Superadas!",
                    team_info="¡Completado al 100%!"
                )
                config.BOT_RUNNING = False
                break
            
        # 3. CAMBIO DE MODO REQUERIDO
        if need_mode_switch:
            _, battle_prep_pt = match_template_single(screen_cv, "battle")
            _, copy_prep_pt = match_template_single(screen_cv, "copy")
            _, use_prep_pt = match_template_single(screen_cv, "use_btn")
            
            if battle_prep_pt or copy_prep_pt or use_prep_pt:
                matched = True
                if copy_prep_pt or use_prep_pt:
                    print("[BOT] Panel de registros abierto durante solicitud de cambio de modo. Cerrando panel...")
                    simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                    time.sleep(0.6)
                    continue
                    
                _, atras_pt = match_template_single(screen_cv, "atras")
                if atras_pt:
                    print("[BOT] Saliendo de la pantalla de preparación para alternar modo...")
                    simulate_human_click(window, atras_pt[0], atras_pt[1])
                    time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.5)
                    continue
                    
        # 4. PANTALLA DE PREPARACIÓN DEL COMBATE
        _, battle_pt = match_template_single(screen_cv, "battle")
        _, copy_pt = match_template_single(screen_cv, "copy")
        _, use_pt = match_template_single(screen_cv, "use_btn")
        if (battle_pt or copy_pt or use_pt) and not need_mode_switch:
            matched = True
            
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
                    time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 1.0)
                else:
                    print("[ADVERTENCIA] Intentando iniciar batalla pero el botón 'battle' no es visible.")
                    team_already_copied = False
                continue
            
            if team_type == "custom":
                if copy_pt:
                    print("[RECORDS] El panel de comunidad está abierto pero toca usar formación personalizada. Cerrándolo...")
                    simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                    current_displayed_team_index = 0
                    time.sleep(0.6)
                    continue
                    
                form_panel_open = (use_pt is not None)
                if not form_panel_open:
                    _, form_btn_pt = match_template_single(screen_cv, "formations_btn")
                    if form_btn_pt:
                        print("[FORMACIONES] Abriendo el panel de formaciones personalizadas...")
                        simulate_human_click(window, form_btn_pt[0], form_btn_pt[1])
                        time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.5)
                    else:
                        print("[ADVERTENCIA] Botón de formaciones personalizadas no encontrado.")
                    continue
                else:
                    _, target_header_pt = match_template_single(screen_cv, custom_name)
                    if target_header_pt:
                        print(f"[FORMACIONES] Encontrada cabecera para {custom_name} en Y: {target_header_pt[1]}")
                        use_points = match_template_multi(screen_cv, "use_btn")
                        if use_points:
                            best_use_pt = min(use_points, key=lambda pt: abs(pt[1] - target_header_pt[1]))
                            if abs(best_use_pt[1] - target_header_pt[1]) < 40:
                                print(f"[FORMACIONES] Aplicando formación {custom_name} haciendo clic en Use en Y: {best_use_pt[1]}")
                                simulate_human_click(window, best_use_pt[0], best_use_pt[1])
                                team_already_copied = True
                                time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.8)
                            else:
                                print(f"[ADVERTENCIA] Botón 'Use' más cercano a {custom_name} está muy desalineado ({abs(best_use_pt[1] - target_header_pt[1])}px).")
                        else:
                            print("[ADVERTENCIA] No se encontraron botones 'Use' en el panel de formaciones.")
                    else:
                        print(f"[ADVERTENCIA] No se encontró la formación personalizada {custom_name} en pantalla.")
                        simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                        time.sleep(0.5)
                    continue
            else:
                if use_pt:
                    print("[FORMACIONES] Cerrando panel de formaciones personalizadas para usar comunidad...")
                    simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                    time.sleep(0.5)
                    continue
                    
                if not copy_pt:
                    _, record_pt = match_template_single(screen_cv, "records")
                    if record_pt:
                        print("[BOT] Abriendo el panel de formaciones de la comunidad...")
                        simulate_human_click(window, record_pt[0], record_pt[1])
                        current_displayed_team_index = 0
                        time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.4)
                    else:
                        print("[ADVERTENCIA] Botón de registros no encontrado. Iniciando combate por defecto...")
                        if battle_pt:
                            simulate_human_click(window, battle_pt[0], battle_pt[1])
                            in_battle = True
                            auto_verified_on = False
                            battle_start_time = time.time()
                            no_match_count = 0
                            update_bot_stats(battle_state="En Batalla")
                            time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.8)
                    continue
                else:
                    clicks_needed = current_team_index - current_displayed_team_index
                    if clicks_needed < 0:
                        print(f"[RECORDS] La formación objetivo #{current_team_index + 1} requiere retroceder (actual: #{current_displayed_team_index + 1}). Cerrando panel para reiniciar...")
                        simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                        current_displayed_team_index = 0
                        time.sleep(0.6)
                        continue
                        
                    if clicks_needed > 0:
                        print(f"[RECORDS] Avanzando {clicks_needed} veces para llegar a la formación #{current_team_index + 1} (Índice actual: #{current_displayed_team_index + 1})...")
                        
                        advanced_ok = True
                        for i in range(clicks_needed):
                            if i > 0:
                                time.sleep(0.4)
                                try:
                                    fresh_s = ImageGrab.grab(bbox=bbox, all_screens=True)
                                    fresh_s_cv = cv2.cvtColor(np.array(fresh_s), cv2.COLOR_RGB2BGR)
                                    _, step_next_pt = match_template_single(fresh_s_cv, "next_formation")
                                except Exception:
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
                            print("[RECORDS] Cerrando panel de comunidad para saltar al siguiente equipo disponible...")
                            simulate_human_click(window, int(window.width * 0.25), int(window.height * 0.5))
                            current_displayed_team_index = 0
                            stage_attempt += 1
                            sub_attempt = 0
                            team_already_copied = False
                            time.sleep(0.6)
                            
                            max_stage_att = STRATEGY_SPEC.get("limits", {}).get("max_stage_attempts", 20)
                            if stage_attempt >= max_stage_att:
                                print(f"[MODO] Se han realizado {max_stage_att} intentos en este nivel. Cambiando al otro modo y bloqueándolo allí...")
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
                                time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.5)
                            continue
                        
                try:
                    new_screen = ImageGrab.grab(bbox=bbox, all_screens=True)
                    new_screen_cv = cv2.cvtColor(np.array(new_screen), cv2.COLOR_RGB2BGR)
                    _, fresh_copy_pt = match_template_single(new_screen_cv, "copy")
                except Exception:
                    fresh_copy_pt = copy_pt
                    
                if fresh_copy_pt:
                    print(f"[BOT] Copiando formación seleccionada (Índice: {current_team_index})...")
                    simulate_human_click(window, fresh_copy_pt[0], fresh_copy_pt[1])
                    team_already_copied = True
                    time.sleep(0.9)
                    
                continue
                
        # 5. MENÚ DE SELECCIÓN DE ETAPAS AFK (Phantimal vs Normal Battle)
        _, normal_chall_pt = match_template_single(screen_cv, "normal_challenge")
        _, phant_chall_pt = match_template_single(screen_cv, "phantimal_challenge")
        
        if normal_chall_pt or phant_chall_pt:
            matched = True
            in_battle = False
            auto_verified_on = False
            auto_was_disabled = False
            need_mode_switch = False
            
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
                if mode_locked:
                    print("\n" + "="*60)
                    print("[BLOQUEO] ALCANZADO EL FIN DE LA LISTA Y EL OTRO MODO NO ESTÁ DISPONIBLE.")
                    print("El modo alternativo solicitado no se encuentra visible y el actual está bloqueado.")
                    print("Deteniendo el bot para evitar un bucle de entrada/salida infinito.")
                    print("="*60 + "\n")
                    raise RuntimeError("Ambos modos de juego están bloqueados o el modo alternativo es inaccesible.")
                
                fallback_pt = normal_chall_pt if normal_chall_pt else phant_chall_pt
                print("[BOT] Entrando a la etapa disponible...")
                simulate_human_click(window, fallback_pt[0], fallback_pt[1])
                
            time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.8)
            continue
                
        # 6. ENTRADA GENERAL DESDE EL MENÚ DE INICIO / NAVEGACIÓN
        _, stages_pt = match_template_single(screen_cv, "AFK_stages")
        if stages_pt:
            matched = True
            print("[BOT] Entrando a AFK Stages...")
            simulate_human_click(window, stages_pt[0], stages_pt[1])
            time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.4)
            continue
            
        _, modes_pt = match_template_single(screen_cv, "battle_modes")
        if modes_pt:
            matched = True
            print("[BOT] Entrando al menú de Modos de Batalla...")
            simulate_human_click(window, modes_pt[0], modes_pt[1])
            time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.4)
            continue
            
        # 7. SOPORTE DE POPUPS GENERALES / CERRAR RECOMPENSAS
        _, cerrar_pt = match_template_single(screen_cv, "cerrar")
        if cerrar_pt and not battle_pt:
            matched = True
            print("[BOT] Cerrando popup detectado en pantalla...")
            simulate_human_click(window, cerrar_pt[0], cerrar_pt[1])
            time.sleep(getattr(config, "LOOP_DELAY", 0.4))
            continue
            
        _, tap_exit_pt = match_template_single(screen_cv, "tap_to_exit")
        if tap_exit_pt:
            matched = True
            print("[BOT] Cerrando pantalla mediante 'Tap to exit'...")
            simulate_human_click(window, tap_exit_pt[0], tap_exit_pt[1])
            time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.5)
            continue
            
        # Espera pasiva del bucle si no hay coincidencias
        if not matched:
            no_match_count += 1
            
            if not in_battle and no_match_count >= 15 and no_match_count % 10 == 0:
                print(f"[BOT] Alerta: {no_match_count} ciclos sin coincidencias. Intentando clic de escape seguro...")
                simulate_human_click(window, int(window.width * 0.15), int(window.height * 0.5))
                time.sleep(getattr(config, "LOOP_DELAY", 0.4) + 0.5)
                continue
                
            if no_match_count % 5 == 0:
                print(f"[INFO] Buscando coincidencias... (Ciclo {no_match_count} sin clics)")
                if getattr(config, "DEBUG", False):
                    scores = []
                    for name in ["battle_modes", "AFK_stages", "battle", "victory", "defeat", "copy", "records", "next_formation"]:
                        conf, _ = match_template_single(screen_cv, name)
                        scores.append(f"{name}: {conf:.2f}")
                    print(f"       -> Confianzas: {', '.join(scores)} (Umbral base: {config.CONFIDENCE_THRESHOLD})")
        else:
            no_match_count = 0
            
        time.sleep(getattr(config, "LOOP_DELAY", 0.4))

