# GEMINI.md

Las reglas de este proyecto están en **[AGENTS.md](AGENTS.md)** — fichero compartido que leen todos los asistentes.

Léelo entero antes de tocar nada. Lo crítico:
- Respeta las Reglas Duras (H1 a H6).
- `simulate_human_click` con retardo y margen aleatorio para todos los clics.
- El Failsafe en la esquina superior izquierda `(0, 0)` no se desactiva jamás.
- Verificación obligatoria antes de commit: `ruff check` + `pytest`.
- Explica cada paso en castellano llano antes de programar.
