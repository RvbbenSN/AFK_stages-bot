import os

import config
from src.core.vision import get_template_threshold, load_template, load_templates_spec


def test_templates_spec_loading():
    """Comprueba que specs/templates.yaml existe y contiene plantillas válidas."""
    specs = load_templates_spec()
    assert isinstance(specs, dict)
    assert len(specs) >= 20
    assert "victory" in specs
    assert "defeat" in specs
    assert "all_stages_cleared" in specs

def test_all_spec_templates_exist_and_loadable():
    """Comprueba que cada plantilla declarada en el YAML existe físicamente y se carga con OpenCV."""
    specs = load_templates_spec()
    for name, data in specs.items():
        filename = data.get("filename", f"{name}.jpg")
        file_path = os.path.join(config.IMAGE_DIR, filename)
        assert os.path.exists(file_path), f"El archivo {filename} para la plantilla '{name}' no existe en {config.IMAGE_DIR}"

        img = load_template(name)
        assert img is not None, f"No se pudo cargar la imagen para '{name}' con OpenCV"
        assert len(img.shape) == 3, f"La imagen '{name}' debe tener 3 canales (BGR)"
        assert img.shape[0] > 0 and img.shape[1] > 0, f"Dimensiones inválidas para '{name}'"

def test_thresholds_within_valid_range():
    """Comprueba que todos los umbrales configurados están entre 0.50 y 1.0."""
    specs = load_templates_spec()
    for name, data in specs.items():
        thresh = get_template_threshold(name)
        assert 0.50 <= thresh <= 1.0, f"Umbral fuera de rango para '{name}': {thresh}"
