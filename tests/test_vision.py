import numpy as np

import bot
from src.core.vision import check_auto_skills_status, match_template_single


def test_screen_smaller_than_template_safety():
    """Verifica que una captura más pequeña que la plantilla no provoque un crash de OpenCV."""
    tiny_screen = np.zeros((10, 10, 3), dtype=np.uint8)
    score, pt = match_template_single(tiny_screen, "victory")
    assert score == 0
    assert pt is None

def test_check_auto_skills_off_detection():
    """Verifica que detecta correctamente el estado OFF si el botón gris está en pantalla."""
    sim_screen = np.zeros((200, 200, 3), dtype=np.uint8)
    auto_off_img = bot.load_template("auto_off")
    h, w = auto_off_img.shape[:2]
    sim_screen[50:50+h, 50:50+w] = auto_off_img

    status, pt = check_auto_skills_status(sim_screen)
    assert status == "OFF"
    assert pt is not None
