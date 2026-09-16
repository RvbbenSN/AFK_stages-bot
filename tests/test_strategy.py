import config
from src.modules.afk_stages import get_team_for_attempt


def test_fast_sweep_phase():
    """Comprueba que los primeros pasos corresponden a la fase de barrido rápido (is_fast_sweep=True)."""
    config.USE_CUSTOM_FORMATIONS = True
    
    # Intento 0 -> Comunidad #1 (índice 0, impar 1)
    team_type, team_val, is_sweep = get_team_for_attempt(0)
    assert team_type == "community"
    assert team_val == 0
    assert is_sweep is True

    # Intento 1 -> Comunidad #3 (índice 2, impar 3)
    team_type, team_val, is_sweep = get_team_for_attempt(1)
    assert team_type == "community"
    assert team_val == 2
    assert is_sweep is True

def test_insistence_phase():
    """Comprueba que tras el barrido rápido se entra en la fase de insistencia (is_fast_sweep=False)."""
    config.USE_CUSTOM_FORMATIONS = True
    
    # Los primeros 11 pasos (5 impares + 4 pares + 2 personalizadas) son barrido rápido
    # El paso 11 es la primera formación de insistencia: Comunidad #1 (índice 0)
    team_type, team_val, is_sweep = get_team_for_attempt(11)
    assert team_type == "community"
    assert team_val == 0
    assert is_sweep is False

def test_disabled_custom_formations():
    """Comprueba que si se desactivan las formaciones personalizadas, nunca se devuelven."""
    config.USE_CUSTOM_FORMATIONS = False
    for attempt in range(25):
        team_type, team_val, _ = get_team_for_attempt(attempt)
        assert team_type == "community"
        assert isinstance(team_val, int)

def test_limited_community_teams():
    """Comprueba que si una etapa tiene menos de 10 formaciones comunitarias, no excede el límite conocido."""
    config.USE_CUSTOM_FORMATIONS = True
    max_known = 3
    for attempt in range(20):
        team_type, team_val, _ = get_team_for_attempt(attempt, max_known_community=max_known)
        if team_type == "community":
            assert team_val < max_known
