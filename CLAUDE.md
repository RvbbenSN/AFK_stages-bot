# CLAUDE.md

Las reglas de este proyecto están en **[AGENTS.md](AGENTS.md)** — fichero compartido que leen todos los asistentes.

Léelo entero antes de tocar nada. Resumen de lo crítico:
- Respeta las Reglas Duras (H1 a H6).
- `simulate_human_click` con jitter y micro-delays para todos los clics.
- El Failsafe en `(0, 0)` no se desactiva bajo ningún concepto.
- Verificación antes de commit: `ruff check` + `pytest`.
- Explica antes de programar en castellano llano, sin jerga.
