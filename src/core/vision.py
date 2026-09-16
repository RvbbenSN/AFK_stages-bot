import os

import cv2
import numpy as np
import yaml

import config

TEMPLATES_CACHE = {}
SPECS_DIR = os.path.join(config.BASE_DIR, "specs")
TEMPLATES_SPEC_PATH = os.path.join(SPECS_DIR, "templates.yaml")

def load_templates_spec():
    """
    Carga la especificación declarativa de plantillas desde specs/templates.yaml.
    Retorna un diccionario mapeando template_name -> {threshold, filename, description}.
    """
    if os.path.exists(TEMPLATES_SPEC_PATH):
        try:
            with open(TEMPLATES_SPEC_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and "templates" in data:
                    return data["templates"]
        except Exception as e:
            if getattr(config, "DEBUG", False):
                print(f"[ADVERTENCIA] Error leyendo specs/templates.yaml: {e}")
    return {}

# Carga inicial de especificaciones y umbrales
TEMPLATES_SPEC = load_templates_spec()

def get_template_threshold(template_name):
    """Obtiene el umbral configurado en specs/templates.yaml o el de config.py por defecto."""
    if template_name in TEMPLATES_SPEC:
        return TEMPLATES_SPEC[template_name].get("threshold", config.CONFIDENCE_THRESHOLD)
    return getattr(config, "CONFIDENCE_THRESHOLD", 0.80)

def load_template(base_name):
    """
    Busca una imagen en la carpeta images/ con extensión .jpg o .png.
    Retorna la imagen OpenCV BGR si existe, de lo contrario None.
    Usa TEMPLATES_CACHE para evitar lecturas de disco redundantes.
    """
    if base_name in TEMPLATES_CACHE:
        return TEMPLATES_CACHE[base_name]

    # Comprobar si la spec especifica un nombre de archivo concreto
    filename_candidates = []
    if base_name in TEMPLATES_SPEC and "filename" in TEMPLATES_SPEC[base_name]:
        filename_candidates.append(TEMPLATES_SPEC[base_name]["filename"])

    name_clean = base_name
    for e in [".jpg", ".png"]:
        if name_clean.lower().endswith(e):
            name_clean = name_clean[:-len(e)]

    for ext in [".jpg", ".png"]:
        candidate = name_clean + ext
        if candidate not in filename_candidates:
            filename_candidates.append(candidate)

    for filename in filename_candidates:
        path = os.path.join(config.IMAGE_DIR, filename)
        if os.path.exists(path):
            template = cv2.imread(path)
            if template is not None:
                TEMPLATES_CACHE[base_name] = template
                if getattr(config, "DEBUG", False):
                    print(f"[DEBUG] Plantilla '{base_name}' cargada con éxito como '{filename}'. Tamaño: {template.shape[1]}x{template.shape[0]}")
                return template

    return None

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

    threshold = get_template_threshold(template_name)

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
    threshold = get_template_threshold(template_name)

    loc = np.where(result >= threshold)
    h, w = template.shape[:2]

    points = []
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

    if score_off >= 0.86 and score_off > (score_on + 0.04):
        return "OFF", pt_off
    elif score_on >= 0.86:
        return "ON", pt_on
    return "UNKNOWN", None
