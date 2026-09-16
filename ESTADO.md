# ESTADO — Tablero de Coordinación y Tareas

Este fichero es el **punto de encuentro y sincronización** para cualquier asistente de IA que trabaje en el proyecto.
Todos se coordinan leyendo y actualizando este fichero y registrando las decisiones en la bitácora.

**Cualquier asistente: lee esto ANTES de tocar nada.**

---

## Quién es quién

| Asistente | Dónde vive | Su trabajo |
|---|---|---|
| **Gemini / Antigravity** | IDE Antigravity | Constructor principal: código, modularización, visión y tests. |
| **Claude / Claude Code** | Terminal / CLI | Revisor senior: auditorías de diseño, resolución de atascos complejos. |
| **Rubén (Humano)** | Frente al juego | Dueño del proyecto: decide prioridades, aprueba cambios y prueba en el juego real. |

---

## Reglas de Coordinación

1. **Antes de empezar:** Lee este fichero y `AGENTS.md`.
2. **Al tomar una tarea:** Marca su estado como `EN CURSO — <Tu Nombre>`.
3. **Al terminar:** Ejecuta `ruff` y `pytest`, cambia el estado a `HECHO`, anota qué cambió en la bitácora y haz commit.
4. **Si te bloqueas:** Marca `BLOQUEADO — <Motivo>` y no continúes a ciegas.
5. **No toques** tareas marcadas `EN CURSO` por otro asistente.

---

## Tablero de Tareas

| # | Tarea | Estado | Responsable | Notas |
|---|---|---|---|---|
| 1 | Detección de "All Stages Cleared" y felicitación | HECHO | Gemini | Plantilla guardada, detección en loop y GUI con gema dorada. |
| 2 | Arquitectura Modular y SDD (`specs/`, `core/`, `tests/`) | HECHO | Gemini | Core extraído (vision, inputs, window), specs YAML, 7 tests unitarios en verde y ruff limpio. |
| 3 | Lector OCR de etapa actual (Battle Prep / Lobby) | PENDIENTE | Por asignar | Pendiente de captura tras nuevo reset/temporada de etapas. |
| 4 | Módulo Homestead (Síntesis de materiales y quests diarias) | PENDIENTE | Por asignar | Se desarrollará en `src/modules/homestead.py` de forma aislada. |

---

## Bitácora

- **2026-09-16** (Gemini) — **Inicio de transición a arquitectura modular y SDD**:
  - Creación de la rama `feature/sdd-modular-architecture`.
  - Instalación de `pyyaml`, `pytest` y `ruff` en `.venv`.
  - Creación de `AGENTS.md`, `ESTADO.md`, `GEMINI.md` y `CLAUDE.md`.
  - Definición de especificaciones declarativas (`specs/templates.yaml`, `specs/battle_strategy.yaml`).
  - Extracción de `src/core/` (`vision.py`, `inputs.py`, `window.py`) y suite de tests offline.
- **2026-09-15** (Gemini) — **Implementación de All Stages Cleared**:
  - Incorporada la plantilla `images/all_stages_cleared.jpg` con umbral 0.82.
  - Parada segura del bot y mensaje conmemorativo al completar el 100% de etapas.
  - Estado dorado `¡COMPLETADO!` en el dashboard de `gui.py`.
